import json
from googleapiclient.errors import HttpError

from pypika import functions
import frappe
from frappe import _
from frappe.desk.reportview import get_filters_cond
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.integrations.doctype.google_calendar.google_calendar import (
    get_google_calendar_object,
    format_date_according_to_google_calendar,
)
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Sum
import io
from openpyxl import Workbook

from frappe.utils import (
    get_fullname,
    now_datetime,
    get_datetime,
    add_to_date,
    flt,
    getdate,
    cint,
    time_diff_in_seconds,
)

from erpnext.crm.doctype.appointment.appointment import Appointment as BaseAppointment
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class Appointment(BaseAppointment):
    def __setup__(self):
        self.flags.update_related_appointments = True

    def create_calendar_event(self):
        pass

    def validate(self):
        if self.docstatus == 0:
            self.set("status", "Draft")

        if not self.scheduled_time:
            self.scheduled_time = now_datetime()

        hours_to_add = flt(
            frappe.db.get_single_value(
                "Appointment Booking Settings", "custom_default_travel_hours"
            )
        )
        if not self.custom_ends_on:
            for row in self.custom_appointment_services:
                hours_to_add += flt(row.working_hours)
            self.custom_ends_on = add_to_date(self.scheduled_time, hours=hours_to_add)

        if self.scheduled_time and self.custom_ends_on:
            self.validate_from_to_dates("scheduled_time", "custom_ends_on")

        if self.custom_sync_with_google_calendar and not self.custom_google_calendar:
            frappe.throw(_("Select Google Calendar to which event should be synced."))

        self.validate_groomer_rest_time()
        self.set_total_pets()
        self.update_totals()
        self.set_booking_message()

    def before_save(self):
        self.set_party_email()

    def before_submit(self):
        self.status = "Open"

    def on_cancel(self):
        self.db_set("status", "Cancelled")
        if self.flags.update_related_appointments:
            self.update_all_related_appointments()
        self.update_consumed_qty(qty=-1)

    def on_submit(self):
        self.sync_communication()
        if self.flags.update_related_appointments:
            self.update_all_related_appointments()
        self.update_consumed_qty(qty=1)
        settings = frappe.get_single("Commissions and Gratuity")
        if (
            cint(settings.enabled_commission) == 1
            and settings.add_on == "Submit Appointment"
        ):
            self.add_commissions(settings)

    def add_commissions(self, settings):
        return
        for vae in self.custom_vehicle_assignment_employees:
            if not vae.employee or not settings.salary_component:
                continue
            employee = vae.employee
            salary_component = settings.salary_component
            commission = 0
            if vae.assign_as == "Groomer":
                commission = flt(settings.groomer_commission)
            elif vae.assign_as == "Driver":
                commission = flt(settings.driver_commission)
            elif vae.assign_as == "Other":
                commission = flt(settings.other_commission)

            if commission <= 0:
                continue

            amount = commission * flt(self.custom_total_net_amount) / 100
            if amount <= 0:
                continue
            additional_salary = frappe.new_doc("Additional Salary")
            company = frappe.db.get_value("Employee", employee, "company")
            additional_salary.update(
                {
                    "employee": employee,
                    "company": company,
                    "salary_component": salary_component,
                    "amount": amount,
                    "payroll_date": add_to_date(getdate(self.scheduled_time), months=1),
                }
            )
            additional_salary.flags.ignore_permissions = True
            additional_salary.save()

    def update_consumed_qty(self, qty=1):
        for service in self.custom_appointment_services:
            if not service.subscription or not service.subscription_row:
                continue
            exists = frappe.db.exists(
                "Package Service Subscription Details",
                {"name": service.subscription_row, "parent": service.subscription},
            )
            if not exists:
                continue
            doc = frappe.get_doc("Package Service Subscription Details", exists)
            if qty > 0 and doc.consumed_qty >= doc.package_qty:
                continue
            if qty < 0 and doc.consumed_qty == 0:
                continue

            consumed_qty = doc.consumed_qty + qty
            if consumed_qty > doc.package_qty:
                continue
            if consumed_qty < 0:
                continue
            doc.db_set("consumed_qty", consumed_qty, update_modified=False)

    def set_total_pets(self):
        self.custom_total_pets = len(
            set(
                filter(
                    lambda x: x, map(lambda x: x.pet, self.custom_appointment_services)
                )
            )
        )

    def update_totals(self):
        self.custom_total_amount = 0
        self.custom_total_net_amount = 0
        self.custom_total_amount_to_pay = 0
        self.custom_total_working_hours = 0
        # addons
        for row in self.custom_appointment_addons:
            self.custom_total_amount += flt(row.rate)
            self.custom_total_net_amount += flt(row.rate)
            self.custom_total_amount_to_pay += flt(row.rate)

        # service items
        for row in self.custom_appointment_services:
            price = flt(row.price)
            self.custom_total_amount += price
            self.custom_total_net_amount += price
            if not row.subscription:
                self.custom_total_amount_to_pay += flt(row.price)
            self.custom_total_working_hours += cint(row.working_hours)

        if self.custom_additional_discount_as == "Percent":
            self.custom_total_net_amount = flt(self.custom_total_net_amount) - (flt(self.custom_total_net_amount) * flt(self.custom_additional_discount)) / 100
            self.custom_total_amount_to_pay = flt(self.custom_total_amount_to_pay) - (flt(self.custom_total_amount_to_pay) * flt(self.custom_additional_discount)) / 100
        elif self.custom_additional_discount_as == "Fixed Amount":
            if flt(self.custom_additional_discount) > flt(self.custom_total_amount_to_pay):
                frappe.throw(_("Discount amount can not be greater than required amount to pay"))
            self.custom_total_net_amount = flt(self.custom_total_net_amount) - flt(self.custom_additional_discount)
            self.custom_total_amount_to_pay = flt(self.custom_total_amount_to_pay) - flt(self.custom_additional_discount)

    def set_booking_message(self):
        template = (
            frappe.db.get_single_value(
                "Appointment Booking Settings", "custom_booking_template_message"
            )
            or ""
        )
        context = self.as_dict()
        pets_services = []
        for row in self.custom_appointment_services:
            pet_name = frappe.db.get_value("Pet", row.pet, "pet_name")
            pets_services.append(f"{pet_name} - {row.service}")
        pets_services = "\n".join(pets_services)
        context.update(
            {
                "pets_services": pets_services,
            }
        )
        template_message = frappe.render_template(template, context=context)
        self.custom_appointment_message = template_message

    def validate_groomer_rest_time(self):
        # TODO(fix validations)
        return
        if not self.custom_groomer:
            return
        rest_time = cint(
            frappe.db.get_single_value(
                "Appointment Booking Settings", "custom_rest_time"
            )
        )
        msg = _("This groomer already has an overlapping appointment.")
        if rest_time > 0:
            msg = _(
                "There must be at least a {}-minute gap between appointments."
            ).format(rest_time)
        start_time = get_datetime(self.scheduled_time)
        end_time = get_datetime(self.custom_ends_on)

        start_time = add_to_date(start_time, minutes=-rest_time)
        end_time = add_to_date(end_time, minutes=rest_time)
        Appointment = frappe.qb.DocType("Appointment")
        overlapping = (
            frappe.qb.from_(Appointment)
            .select(Appointment.name)
            .where(
                (Appointment.custom_groomer == self.custom_groomer)
                & (Appointment.name != self.name)
                & (Appointment.docstatus != 2)
                & (
                    (Appointment.scheduled_time < end_time)
                    & (Appointment.custom_ends_on > start_time)
                )
            )
        ).run(as_dict=True)
        if overlapping:
            frappe.throw(msg)

    def update_all_related_appointments(self):
        # TODO(fix employees)
        return
        if (
            cint(
                frappe.db.get_single_value(
                    "Appointment Booking Settings",
                    "custom_reschedule_all_linked_appointments",
                )
            )
            == 0
        ):
            return
        if self.status != "Closed":
            return
        # check if ends time is updated and status is closed
        prev_doc = self.get_doc_before_save()
        if not prev_doc:
            return
        time_diff = time_diff_in_seconds(self.custom_ends_on, prev_doc.custom_ends_on)
        if (time_diff == 0) or prev_doc.status == "Closed":
            return

        Appointment = frappe.qb.DocType("Appointment")
        query = (
            frappe.qb.from_(Appointment)
            .select(Appointment.name)
            .where(
                (Appointment.custom_employee == self.custom_employee)
                & (Appointment.name != self.name)
                & (Appointment.status == "Open")
                & (Appointment.scheduled_time >= self.custom_ends_on)
                & (
                    functions.Date(Appointment.scheduled_time)
                    == getdate(self.custom_ends_on)
                )
            )
        )
        appointments = query.run(as_dict=True)
        if len(appointments) == 0:
            return
        for appointment in appointments:
            appointment = frappe.get_doc("Appointment", appointment)

            appointment.flags.update_related_appointments = False
            appointment.scheduled_time = add_to_date(
                appointment.scheduled_time, seconds=time_diff
            )
            appointment.custom_ends_on = add_to_date(
                appointment.custom_ends_on, seconds=time_diff
            )
            appointment.flags.ignore_permissions = True
            appointment.flags.ignore_mandatory = True
            appointment.save()

    @frappe.whitelist()
    def complete_appointment(self, update_ends_time=False):
        if self.status != "Open":
            return
        self.db_set("status", "Completed Not Paid")
        if not update_ends_time:
            return "ok"

        if not self.custom_ends_on:
            self.db_set("custom_ends_on", now_datetime())
            if self.flags.update_related_appointments:
                self.update_all_related_appointments()
            return "ok"

        if time_diff_in_seconds(self.custom_ends_on, now_datetime()) <= 0:
            if self.flags.update_related_appointments:
                self.update_all_related_appointments()
            return "ok"
        self.db_set("custom_ends_on", now_datetime())
        if self.flags.update_related_appointments:
            self.update_all_related_appointments()
        return "ok"

    @frappe.whitelist()
    def close_appointment(self):
        if self.status != "Open":
            return
        self.db_set("status", "Closed")
        return "ok"

    @frappe.whitelist()
    def re_open_appointment(self):
        if self.status != "Closed":
            return
        self.db_set("status", "Open")
        return "ok"

    @frappe.whitelist()
    def create_invoice_appointment(self, update_ends_time=False, due_date=None, payments_details=[], tip_amount=0):
        if self.docstatus == "Completed" or self.custom_sales_invoice:
            return
        
        # Distribute received tip
        tip_amount = flt(tip_amount)
        tip_len = len(self.custom_vehicle_assignment_employees or [])
        if tip_amount > 0 and tip_len > 0:
            tip_amount1 = tip_amount / tip_len
            for emp in self.custom_vehicle_assignment_employees:
                doc = frappe.new_doc("Appointment Tips Ledger")
                doc.update({
                    "appointment": self.name,
                    "tips_received": tip_amount,
                    "employee": emp.employee,
                    "employee_name": emp.employee_name,
                    "tip_value": tip_amount1,
                    "tip_percent": 100 / tip_len
                })
                doc.save(ignore_permissions=True)

        # Create Invoice
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.party
        invoice.posting_date = getdate()
        invoice.due_date = getdate(due_date) if due_date else getdate()

        for service in self.custom_appointment_services:
            if (
                not service.service
                or not service.service_item
                or (service.subscription)
            ):
                continue
            doc = frappe.get_doc("Pet Service Item", service.service_item)
            rate = flt(service.price)
            if flt(service.discount) > 0:
                rate = rate - (flt(service.discount) * rate / 100)
            item = {
                "item_code": doc.item,
                "uom": doc.uom,
                "qty": 1,
                "rate": rate,
            }
            if rate <= 0:
                item.update({
                    "rate": 0,
                    "discount_percentage": 100,
                })

            invoice.append(
                "items",
                item,
            )
        for addon in self.custom_appointment_addons:
            if not addon.service_addon or not addon.item:
                continue
            rate = flt(addon.rate)
            item = {
                "item_code": addon.item,
                "uom": addon.uom,
                "qty": 1,
                "rate": rate,
            }

            invoice.append(
                "items",
                item,
            )

        if len(invoice.items) == 0:
            self.db_set("status", "Completed")
            return

        additional_discount = flt(self.custom_additional_discount)
        if additional_discount > 0:
            if self.custom_additional_discount_as == "Fixed Amount":
                invoice.discount_amount = additional_discount
            elif self.custom_additional_discount_as == "Percent":
                invoice.additional_discount_percentage = additional_discount
        
        invoice.flags.ignore_permissions = True
        invoice.save()
        invoice.submit()

        # Make payments against invoice
        for payment in payments_details:
            mode_of_payment = payment.get("mode_of_payment")
            paid_amount = flt(payment.get("paid_amount"))
            if not mode_of_payment or paid_amount == 0:
                continue
            payment_doc = get_payment_entry(
                dt="Sales Invoice", dn=invoice.name, ignore_permissions=True
            )
            payment_doc.mode_of_payment = mode_of_payment
            payment_doc.references[0].allocated_amount = paid_amount
            payment_doc.flags.ignore_permissions = True
            payment_doc.save()
            payment_doc.submit()
        self.db_set("status", "Completed")
        self.db_set("custom_sales_invoice", invoice.name)

        # Add Commissions
        settings = frappe.get_single("Commissions and Gratuity")
        if (
            cint(settings.enabled_commission) == 1
            and settings.add_on == "Complete Appointment"
        ):
            self.add_commissions(settings)
        if not update_ends_time:
            return "ok"

        if not self.custom_ends_on:
            self.db_set("custom_ends_on", now_datetime())
            if self.flags.update_related_appointments:
                self.update_all_related_appointments()
            return "ok"

        if time_diff_in_seconds(self.custom_ends_on, now_datetime()) <= 0:
            return "ok"
        self.db_set("custom_ends_on", now_datetime())
        if self.flags.update_related_appointments:
            self.update_all_related_appointments()
        return "ok"

    def on_trash(self):
        communications = frappe.get_all(
            "Communication",
            filters={"reference_doctype": self.doctype, "reference_name": self.name},
            pluck="name",
        )
        for communication in communications:
            frappe.delete_doc("Communication", communication, force=True)

    def sync_communication(self):
        # TODO(Fix employees)
        return
        event_participants = []
        if self.custom_employee:
            p1 = frappe._dict()
            p1.update(
                {
                    "reference_doctype": "Employee",
                    "reference_docname": self.custom_employee,
                }
            )
            event_participants.append(p1)

        if self.appointment_with and self.party:
            p1 = frappe._dict()
            p1.update(
                {
                    "reference_doctype": self.appointment_with,
                    "reference_docname": self.party,
                }
            )
            event_participants.append(p1)

        if not event_participants:
            return

        for participant in event_participants:
            if communications := frappe.get_all(
                "Communication",
                filters=[
                    ["Communication", "reference_doctype", "=", self.doctype],
                    ["Communication", "reference_name", "=", self.name],
                    [
                        "Communication Link",
                        "link_doctype",
                        "=",
                        participant.reference_doctype,
                    ],
                    [
                        "Communication Link",
                        "link_name",
                        "=",
                        participant.reference_docname,
                    ],
                ],
                pluck="name",
                distinct=True,
            ):
                for comm in communications:
                    communication = frappe.get_doc("Communication", comm)
                    self.update_communication(participant, communication)
            else:
                meta = frappe.get_meta(participant.reference_doctype)
                if (
                    hasattr(meta, "allow_events_in_timeline")
                    and meta.allow_events_in_timeline == 1
                ):
                    self.create_communication(participant)

    def create_communication(self, participant):
        communication = frappe.new_doc("Communication")
        self.update_communication(participant, communication)
        self.communication = communication.name

    def update_communication(
        self,
        participant,
        communication,
    ):
        communication.communication_medium = "Event"
        communication.subject = self.custom_subject
        communication.content = (
            self.customer_details if self.customer_details else self.custom_subject
        )
        communication.communication_date = self.scheduled_time
        communication.sender = self.owner
        communication.sender_full_name = get_fullname(self.owner)
        communication.reference_doctype = self.doctype
        communication.reference_name = self.name
        communication.communication_medium = "Meeting"
        communication.status = "Linked"
        communication.add_link(
            participant.reference_doctype, participant.reference_docname
        )
        communication.save(ignore_permissions=True)

    def set_party_email(self):
        if self.appointment_with and self.party:
            party_contact = get_default_contact(self.appointment_with, self.party)
            email = (
                frappe.get_value("Contact", party_contact, "email_id")
                if party_contact
                else None
            )
            self.customer_email = email

    def after_insert(self):
        insert_event_in_google_calendar(self)

    def check_discount_values(self):
        if (
            self.custom_additional_discount_as == "Percent"
            and flt(self.custom_additional_discount) > 100
        ):
            frappe.throw(_("Discount Percent can not be greater that 100"))
        total_price = 0
        total_net_price = 0
        total_hours = 0
        total_amount_to_pay = 0

        for row in self.custom_appointment_addons:
            total_price += flt(row.rate)
            total_net_price += flt(row.rate)
            total_amount_to_pay += flt(row.rate)

        for row in self.custom_appointment_services:
            total_price += flt(row.price)
            total_hours += flt(row.working_hours)
            amount = 0
            if row.discount_as == "Percent":
                amount = flt(row.price) - (flt(row.price) * flt(row.discount)) / 100
            elif row.discount_as == "Fixed Amount":
                amount = flt(row.price) - flt(row.discount)
            else:
                amount = flt(row.price)
            total_net_price += amount
            if not row.sales_invoice:
                total_amount_to_pay += amount

        if self.custom_additional_discount_as == "Fixed Amount" and flt(
            self.custom_additional_discount
        ) > flt(total_amount_to_pay):
            frappe.throw(
                _(
                    "Discount Amount can not be greater that total price {}".format(
                        total_amount_to_pay
                    )
                )
            )
        if self.custom_additional_discount_as == "Percent":
            total_net_price = (
                flt(total_net_price)
                - (flt(total_net_price) * flt(self.custom_additional_discount)) / 100
            )
            total_amount_to_pay = (
                flt(total_amount_to_pay)
                - (flt(total_amount_to_pay) * flt(self.custom_additional_discount))
                / 100
            )
        elif self.custom_additional_discount_as == "Fixed Amount":
            total_net_price = flt(total_net_price) - flt(
                self.custom_additional_discount
            )
            total_amount_to_pay = flt(total_amount_to_pay) - flt(
                self.custom_additional_discount
            )

        return total_price, total_net_price, total_hours, total_amount_to_pay

    @frappe.whitelist()
    def set_vehicle_employees(self, vehicle=None):
        if not vehicle:
            return []
        assignments = frappe.get_all(
            "Vehicle Assignment",
            filters={"status": "Active", "vehicle": vehicle},
        )
        if len(assignments) > 0:
            return frappe.get_all(
                "Vehicle Assignment Employee",
                filters={"parent": assignments[0].name},
                fields="*",
            )
        frappe.msgprint(_("There is employees assigned to vehicle {}").format(vehicle))
        return []

    @frappe.whitelist()
    def fetch_service_item_subscription(self, service=None, pet=None):
        pet = frappe.db.exists("Pet", pet)
        service = frappe.db.exists("Pet Service", service)
        if not service or not pet:
            frappe.msgprint(_("Select Pet and Service to fetch details"))
            return
        pet = frappe.get_doc("Pet", pet)
        service_item = self.get_service_item(service, pet.pet_size, pet.pet_type)
        if not service_item:
            return

        price = frappe.db.get_value("Pet Service Item", service_item, "rate") or 0.0
        if (
            self.appointment_with != "Customer"
            or service is None
            or service_item is None
            or not self.party
        ):
            return {
                "price": price,
                "service_item": service_item,
            }
        packages_with_item = frappe.get_all(
            "Package Service",
            {"service": service, "service_item": service_item},
            pluck="parent",
        )
        if len(packages_with_item) == 0:
            return {
                "price": price,
                "service_item": service_item,
            }
        PetPackageSubscription = frappe.qb.DocType("Pet Package Subscription")
        PackageSubscriptionDetails = frappe.qb.DocType(
            "Package Service Subscription Details"
        )
        query = (
            frappe.qb.from_(PackageSubscriptionDetails)
            .left_join(PetPackageSubscription)
            .on(PetPackageSubscription.name == PackageSubscriptionDetails.parent)
            .select(
                PetPackageSubscription.name,
                PackageSubscriptionDetails.pet_service_package,
                PackageSubscriptionDetails.package_qty,
                PackageSubscriptionDetails.consumed_qty,
                PackageSubscriptionDetails.name.as_("row_name"),
            )
            .where(
                (PetPackageSubscription.customer == self.party)
                & (
                    PackageSubscriptionDetails.pet_service_package.isin(
                        packages_with_item
                    )
                )
                & (
                    PackageSubscriptionDetails.package_qty
                    > PackageSubscriptionDetails.consumed_qty
                )
            )
            .orderby(PetPackageSubscription.subscription_at)
        )
        data = query.run(as_dict=True)
        if len(data) == 0:
            return {
                "price": price,
                "service_item": service_item,
            }
        # check if the item is selected in same appointment
        for r in self.custom_appointment_services:
            if not r.subscription or not r.subscription_row:
                continue
            for d in data:
                if r.subscription == d.name and r.subscription_row == d.row_name:
                    consumed_qty = d.consumed_qty + 1
                    d.update(
                        {
                            "consumed_qty": consumed_qty,
                        }
                    )
        data = list(filter(lambda x: x.consumed_qty < x.package_qty, data))
        if len(data) == 0:
            return {
                "price": price,
                "service_item": service_item,
            }
        data = data[0]
        remaining_sessions = cint(data["package_qty"]) - cint(data["consumed_qty"])
        if remaining_sessions < 0:
            remaining_sessions = 0
        data.update({
            "remaining_sessions": remaining_sessions,
        })
        # add item price
        subscription = frappe.get_doc("Pet Package Subscription", data.name)
        row = None
        for p in subscription.package_services:
            if p.name == data.row_name:
                row = p
                break
        if row:
            diff_percent = (
                (row.selling_amount - row.total_amount) * 100 / row.total_amount
            )
            price = price - (diff_percent * price / 100)
            price = price - (row.discount * price / 100)
            data.update(
                {
                    "price": price,
                    "service_item": service_item,
                }
            )
        else:
            data.update(
                {
                    "price": price,
                    "service_item": service_item,
                }
            )

        return data

    @frappe.whitelist()
    def get_service_item(self, service, pet_size, pet_type):
        print(service, pet_size, pet_type)
        print(service, pet_size, pet_type)
        print(service, pet_size, pet_type)
        print(service, pet_size, pet_type)
        print(service, pet_size, pet_type)
        valid_items_both = set()
        valid_items_type_only = set()
        valid_items_size_only = set()

        if pet_type and pet_size:
            valid_items_both = set(
                frappe.db.sql(
                    """
                    SELECT DISTINCT t1.parent
                    FROM `tabPet Service Item Type` t1
                    INNER JOIN `tabPet Service Item Size` t2 ON t1.parent = t2.parent
                    WHERE t1.pet_type = %(pet_type)s
                    AND t2.pet_size = %(pet_size)s
                    """,
                    {"pet_type": pet_type, "pet_size": pet_size},
                    pluck="parent",
                )
            )
        if pet_type:
            valid_items_type_only = set(
                frappe.db.sql(
                    """
                    SELECT DISTINCT t1.parent
                    FROM `tabPet Service Item Type` t1
                    LEFT JOIN `tabPet Service Item Size` t2 ON t1.parent = t2.parent
                    WHERE t1.pet_type = %(pet_type)s
                    AND (t2.pet_size IS NULL OR t2.pet_size = '')
                    """,
                    {"pet_type": pet_type},
                    pluck="parent",
                )
            )
        if pet_size:
            valid_items_size_only = set(
                frappe.db.sql(
                    """
                    SELECT DISTINCT t2.parent
                    FROM `tabPet Service Item Size` t2
                    LEFT JOIN `tabPet Service Item Type` t1 ON t1.parent = t2.parent
                    WHERE t2.pet_size = %(pet_size)s
                    AND (t1.pet_type IS NULL OR t1.pet_type = '')
                    """,
                    {"pet_size": pet_size},
                    pluck="parent",
                )
            )
        valid_items = valid_items_both | valid_items_type_only | valid_items_size_only
        if not valid_items:
            frappe.msgprint(_("No valid item found for the pet"))
            return None

        exists = frappe.db.exists(
            "Pet Service Item Detail",
            {"parent": service, "pet_service_item": ["in", valid_items]},
        )
        if exists:
            doc = frappe.get_doc("Pet Service Item Detail", exists)
            rate = flt(doc.rate)
            if doc.discount_as == "Percent":
                rate = rate - (flt(doc.discount) * rate / 100)
            if doc.discount_as == "Fixed Amount":
                rate = rate - flt(doc.discount)
            return doc.pet_service_item
        else:
            frappe.msgprint(_("No valid item found for the pet"))
        return None


@frappe.whitelist()
def get_appointments(
    start, end, user=None, for_reminder=False, filters=None
) -> list[frappe._dict]:
    if not user:
        user = frappe.session.user

    if isinstance(filters, str):
        filters = json.loads(filters)

    filter_condition = get_filters_cond("Appointment", filters, [])

    tables = ["`tabAppointment`"]
    if "`tabAppointment Participants`" in filter_condition:
        tables.append("`tabAppointment Participants`")
    Appointment = frappe.qb.DocType("Appointment")
    # DocShare = frappe.qb.DocType("DocShare")

    # share_query = ExistsCriterion(
    #     frappe.qb.from_(DocShare)
    #     .select(1)
    #     .where(
    #         (DocShare.share_doctype == "Appointment")
    #         & (DocShare.share_name == Appointment.name)
    #         & (DocShare.user == user)
    #     )
    # )
    query = (
        frappe.qb.from_(Appointment)
        .select(
            Appointment.name,
            Appointment.status,
            functions.IfNull(Appointment.custom_vehicle, "unassigned").as_(
                "resourceId"
            ),  # resourceId for calendar-view
            Appointment.custom_vehicle.as_("vehicle"),
            Appointment.custom_vehicle,
            Appointment.custom_area,
            Appointment.customer_name,
            Appointment.customer_phone_number,
            Appointment.custom_subject,
            Appointment.custom_total_pets,
            Appointment.docstatus,
            Appointment.status,
            Appointment.customer_details.as_("description"),
            Appointment.custom_color.as_("color"),
            Appointment.scheduled_time.as_("scheduled_time"),
            Appointment.custom_ends_on,
            Appointment.owner,
            Appointment.custom_send_reminder.as_("send_reminder"),
            ConstantColumn(0).as_("all_day"),
        )
        .where(
            (Appointment.docstatus != 2)
            & (
                functions.Date(Appointment.scheduled_time).between(start, end)
                | functions.Date(Appointment.custom_ends_on).between(start, end)
                | (
                    (functions.Date(Appointment.scheduled_time) <= start)
                    & (functions.Date(Appointment.custom_ends_on) >= end)
                )
            )
            # & ((Appointment.owner == user) | share_query)
        )
    )
    if for_reminder:
        query = query.where(Appointment.custom_send_reminder == 1)

    appointments = query.run(as_dict=True)
    for appointment in appointments:
        subject = ""
        area = appointment.custom_area or ""
        customer_name = appointment.customer_name or ""
        if area:
            subject = f"{customer_name} in ({area})"
        else:
            subject = customer_name
        phone_number = appointment.customer_phone_number or ""
        if phone_number:
            subject += f" : {phone_number}"
        subject1 = appointment.custom_subject or ""
        if subject1:
            subject += f" - {subject1}"
        total_pets = cint(appointment.custom_total_pets or "")
        if total_pets:
            subject += f" ,for {total_pets} (Pets)"
        appointment.update(
            {
                "subject": subject,
            }
        )

    return appointments


@frappe.whitelist()
def update_appointment(args, field_map):
    """Updates Event (called via calendar) based on passed `field_map`"""
    args = frappe._dict(json.loads(args))
    field_map = frappe._dict(json.loads(field_map))

    w = frappe.get_doc(args.doctype, args.name)
    w.set(field_map.start, args[field_map.start])
    w.set(field_map.end, args.get(field_map.end))
    w.set(field_map.resource, args.get(field_map.resource))
    w.save()


# Google Calendar
def insert_event_in_google_calendar(doc):
    """
    Insert Events in Google Calendar if sync_with_google_calendar is checked.
    """
    if (
        not doc.custom_sync_with_google_calendar
        or doc.custom_pulled_from_google_calendar
        or not frappe.db.exists("Google Calendar", {"name": doc.custom_google_calendar})
    ):
        return

    google_calendar, account = get_google_calendar_object(doc.custom_google_calendar)

    if not account.push_to_google_calendar:
        return

    event = {
        "summary": doc.custom_subject,
        "description": doc.customer_details,
        "google_calendar_event": 1,
    }
    event.update(
        format_date_according_to_google_calendar(
            0,
            get_datetime(doc.scheduled_time),
            get_datetime(doc.ends_on) if doc.ends_on else None,
        )
    )

    event.update({"attendees": get_attendees(doc)})

    conference_data_version = 0

    try:
        event = (
            google_calendar.events()
            .insert(
                calendarId=doc.custom_google_calendar_id,
                body=event,
                conferenceDataVersion=conference_data_version,
                sendUpdates="all",
            )
            .execute()
        )

        frappe.db.set_value(
            "Event",
            doc.name,
            {
                "google_calendar_event_id": event.get("id"),
                "google_meet_link": event.get("hangoutLink"),
            },
            update_modified=False,
        )

        frappe.msgprint(_("Event Synced with Google Calendar."))
    except HttpError as err:
        frappe.throw(
            _(
                "Google Calendar - Could not insert event in Google Calendar {0}, error code {1}."
            ).format(account.name, err.resp.status)
        )


def update_event_in_google_calendar(doc, method=None):
    """
    Updates Events in Google Calendar if any existing event is modified in Frappe Calendar
    """
    # Workaround to avoid triggering updating when Event is being inserted since
    # creation and modified are same when inserting doc
    if (
        not doc.custom_sync_with_google_calendar
        or doc.modified == doc.creation
        or not frappe.db.exists("Google Calendar", {"name": doc.custom_google_calendar})
    ):
        return

    if doc.custom_sync_with_google_calendar and not doc.custom_google_calendar_event_id:
        # If sync_with_google_calendar is checked later, then insert the event rather than updating it.
        insert_event_in_google_calendar(doc)
        return

    google_calendar, account = get_google_calendar_object(doc.custom_google_calendar)

    if not account.push_to_google_calendar:
        return

    try:
        event = (
            google_calendar.events()
            .get(
                calendarId=doc.custom_google_calendar_id,
                eventId=doc.custom_google_calendar_event_id,
            )
            .execute()
        )

        event["summary"] = doc.custom_subject
        event["description"] = doc.customer_details
        event["recurrence"] = []
        event["status"] = (
            "cancelled"
            if doc.status == "Cancelled" or doc.status == "Closed"
            else event.get("status")
        )
        event.update(
            format_date_according_to_google_calendar(
                0,
                get_datetime(doc.scheduled_time),
                get_datetime(doc.ends_on) if doc.ends_on else None,
            )
        )

        conference_data_version = 0
        event.update({"attendees": get_attendees(doc)})
        event = (
            google_calendar.events()
            .update(
                calendarId=doc.custom_google_calendar_id,
                eventId=doc.custom_google_calendar_event_id,
                body=event,
                conferenceDataVersion=conference_data_version,
                sendUpdates="all",
            )
            .execute()
        )

        # if add_video_conferencing enabled or disabled during update, overwrite
        frappe.db.set_value(
            "Event",
            doc.name,
            {"google_meet_link": event.get("hangoutLink")},
            update_modified=False,
        )
        doc.notify_update()

        frappe.msgprint(_("Event Synced with Google Calendar."))
    except HttpError as err:
        frappe.throw(
            _(
                "Google Calendar - Could not update Event {0} in Google Calendar, error code {1}."
            ).format(doc.name, err.resp.status)
        )


def delete_event_from_google_calendar(doc, method=None):
    """
    Delete Events from Google Calendar if Frappe Event is deleted.
    """

    if not frappe.db.exists(
        "Google Calendar",
        {"name": doc.custom_google_calendar, "push_to_google_calendar": 1},
    ):
        return

    google_calendar, _ = get_google_calendar_object(doc.custom_google_calendar)

    try:
        event = (
            google_calendar.events()
            .get(
                calendarId=doc.custom_google_calendar_id,
                eventId=doc.custom_google_calendar_event_id,
            )
            .execute()
        )
        event["recurrence"] = None
        event["status"] = "cancelled"

        google_calendar.events().update(
            calendarId=doc.custom_google_calendar_id,
            eventId=doc.custom_google_calendar_event_id,
            body=event,
        ).execute()
    except HttpError as err:
        frappe.msgprint(
            _(
                "Google Calendar - Could not delete Event {0} from Google Calendar, error code {1}."
            ).format(doc.name, err.resp.status)
        )


def get_attendees(doc):
    """
    Returns a list of dicts with attendee emails, if available in event_participants table
    """
    if not doc.customer_email:
        frappe.msgprint(
            _(
                "Google Calendar - Contact / email not found. Did not add email for -<br>{0}"
            ).format(f"{doc.appointment_with} {doc.party}"),
            alert=True,
            indicator="yellow",
        )
    attendees = [doc.customer_email]

    return attendees


@frappe.whitelist()
def bulk_submit(doctype, docnames):
    from frappe.desk.doctype.bulk_update.bulk_update import submit_cancel_or_update_docs

    try:
        docnames = frappe.parse_json(docnames)
    except:  # noqa: E722
        docnames = []
    if not isinstance(docnames, list):
        docnames = []

    return submit_cancel_or_update_docs(doctype, docnames)


@frappe.whitelist()
def export_vehicle_bookings_direct(
    resource_id: str,
    current_date: str,
    range_start: str | None = None,
    range_end: str | None = None,
):
    """Generate an .xlsx in-memory and stream it as a download."""
    # ---- figure out window ----
    if range_start and range_end:
        start_date = getdate(range_start)
        end_date = getdate(range_end)
    else:
        start_date = getdate(current_date)
        end_date = start_date

    start_dt = f"{start_date} 00:00:00"
    end_dt_exclusive = f"{frappe.utils.add_days(end_date, 1)} 00:00:00"

    filters = [
        ["Appointment", "scheduled_time", "<", end_dt_exclusive],
        ["Appointment", "custom_ends_on", ">=", start_dt],
    ]
    if resource_id == "unassigned":
        filters.append(["Appointment", "custom_vehicle", "is", "not set"])
    else:
        filters.append(["Appointment", "custom_vehicle", "=", resource_id])

    rows = frappe.get_all(
        "Appointment",
        filters,
        order_by="scheduled_time asc",
        limit_page_length=10000,
        pluck="name",
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Bookings"
    ws.append([f"Van {resource_id} Schedule"])

    fmt = frappe.utils.format_datetime
    for r in rows:
        appointment = frappe.get_doc("Appointment", r)
        ws.append(["Booking #:", appointment.name])
        ws.append(["Appointment Time:", fmt(appointment.scheduled_time)])
        ws.append(
            [
                "Client Name:",
                appointment.party,
            ]
        )
        ws.append(
            [
                "Mobile Number:",
                appointment.customer_phone_number or "",
            ]
        )
        ws.append(
            [
                "Location Pin:",
                appointment.custom_google_maps_link or "",
            ]
        )
        ws.append(
            [
                "Address:",
                appointment.custom_address or "",
            ]
        )
        ws.append(
            [
                "Number of Pets:",
                appointment.custom_total_pets or "",
            ]
        )
        ws.append(
            [
                "Pet Details:",
                "",
            ]
        )
        addons = [a.service_addon for a in appointment.custom_appointment_addons]
        addons = ", ".join(addons)
        for row in appointment.custom_appointment_services:
            pet = frappe.get_doc("Pet", row.pet)
            idx = row.idx
            service = row.service
            pet_name = pet.pet_name or ""
            pet_type = pet.pet_type or ""
            pet_size = pet.pet_size or ""
            ws.append(
                [
                    "",
                    f"• {idx}: {pet_name}, {pet_type}, {pet_size}, {service}, {addons}",
                ]
            )

        ws.append(
            [
                "Total Price:",
                appointment.custom_total_net_amount or "",
            ]
        )
        # ws.append([
        #     r.name, r.subject or "", r.custom_vehicle or "", r.customer or "", r.status or "",
        #     fmt(r.scheduled_time) if r.scheduled_time else "",
        #     fmt(r.custom_ends_on) if r.custom_ends_on else "",
        #     r.owner or "", fmt(r.creation) if r.creation else "", fmt(r.modified) if r.modified else ""
        # ])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    pretty = resource_id if resource_id != "unassigned" else "Unassigned"
    filename = f"VehicleBookings-{pretty}-{start_date}"
    if end_date != start_date:
        filename += f"-to-{end_date}"
    filename += ".xlsx"

    # ---- stream as download ----
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = bio.getvalue()
    frappe.local.response.type = "download"
