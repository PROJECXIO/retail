import json
from googleapiclient.errors import HttpError

from pypika import functions
from pypika.terms import ExistsCriterion

import frappe
from frappe import _
from frappe.desk.reportview import get_filters_cond
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.integrations.doctype.google_calendar.google_calendar import (
    get_google_calendar_object,
    format_date_according_to_google_calendar,
)
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Concat

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

        # if start == end this scenario doesn't make sense i.e. it starts and ends at the same second!
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
        total_price, total_net_price, total_hours = self.check_discount_values()
        self.custom_total_amount = total_price
        self.custom_total_net_amount = total_net_price
        self.custom_total_working_hours = total_hours

        self.validate_groomer_rest_time()
        self.set_total_pets()

    def before_save(self):
        self.set_party_email()

    def before_submit(self):
        self.status = "Open"

    def on_cancel(self):
        self.db_set("status", "Cancelled")
        if self.flags.update_related_appointments:
            self.update_all_related_appointments()

    def on_submit(self):
        self.sync_communication()
        if self.flags.update_related_appointments:
            self.update_all_related_appointments()

    def set_total_pets(self):
        self.custom_total_pets = len(self.custom_appointment_services)

    def validate_groomer_rest_time(self):
        if not self.custom_groomer:
            return

        rest_time = cint(frappe.db.get_single_value("Appointment Booking Settings", "custom_rest_time"))
        start_time = get_datetime(self.start_time)
        end_time = get_datetime(self.end_time)

        overlapping = (
            frappe.qb.from_(Appointment)
            .select(Appointment.name)
            .where(
                (Appointment.employee == self.employee)
                & (Appointment.name != self.name)
                & (Appointment.docstatus != 2)
                & (
                        (Appointment.start_time < end_time)
                        & (Appointment.end_time > start_time)
                    )
                )
            ).run(as_dict=True)
        if overlapping:
            frappe.throw(_("This employee already has an overlapping appointment."))
        if rest_time <= 0:
            return
        gap_start = add_to_date(start_time, minutes=-rest_time)
        gap_end = add_to_date(end_time, minutes=rest_time)

        no_gap = (
            frappe.qb.from_(Appointment)
            .select(Appointment.name)
            .where(
                (Appointment.employee == self.employee)
                & (Appointment.name != self.name)
                & (Appointment.docstatus != 2)
                & (
                    (Appointment.end_time > gap_start)
                    & (Appointment.start_time < gap_end)
                )
            )
        ).run(as_dict=True)
        if no_gap:
            frappe.throw(_("There must be at least a {}-minute gap between appointments.").format(rest_time))
        
    def update_all_related_appointments(self):
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
    def create_invoice_appointment(self, update_ends_time=False, payments_details=[]):
        if self.status != "Open" and self.status != "Completed Not Paid":
            return

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.party
        invoice.posting_date = getdate()
        invoice.due_date = getdate()
        for service in self.custom_appointment_services:
            if not service.service or not service.service_item:
                continue
            doc = frappe.get_doc("Pet Service Item", service.service_item)
            rate = flt(service.price)
            if flt(service.discount) > 0:
                if service.discount_as == "Percent":
                    rate = rate - (flt(service.discount) * rate / 100)
                elif service.discount_as == "Fixed Amount":
                    rate = rate - flt(service.discount)
            item = {
                "item_code": doc.item,
                "uom": doc.uom,
                "qty": 1,
                "rate": rate,
            }

            invoice.append(
                "items",
                item,
            )
        additional_discount = flt(self.custom_additional_discount)
        if additional_discount > 0:
            if self.custom_additional_discount_as == "Fixed Amount":
                invoice.discount_amount = additional_discount
            elif self.custom_additional_discount_as == "Percent":
                invoice.discount_amount = additional_discount
        invoice.flags.ignore_permissions = True
        invoice.save()
        invoice.submit()

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

    def create_communication(self, participant: "EventParticipants"):
        communication = frappe.new_doc("Communication")
        self.update_communication(participant, communication)
        self.communication = communication.name

    def update_communication(
        self, participant: "EventParticipants", communication: "Communication"
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

        if self.custom_additional_discount_as == "Fixed Amount" and flt(
            self.custom_additional_discount
        ) > flt(total_net_price):
            frappe.throw(
                _(
                    "Discount Amount can not be greater that total price {}".format(
                        total_net_price
                    )
                )
            )
        if self.custom_additional_discount_as == "Percent":
            total_net_price = (
                flt(total_net_price)
                - (flt(total_net_price) * flt(self.custom_additional_discount)) / 100
            )
        elif self.custom_additional_discount_as == "Fixed Amount":
            total_net_price = flt(total_net_price) - flt(
                self.custom_additional_discount
            )

        return total_price, total_net_price, total_hours

    @frappe.whitelist()
    def fetch_service_item(self, service, pet_size, pet_type):
        exists = frappe.db.exists(
            "Pet Service Item Detail",
            {"parent": service, "pet_size": pet_size or "", "pet_type": pet_type or ""},
        )
        if exists:
            doc = frappe.get_doc("Pet Service Item Detail", exists)
            rate = flt(doc.rate)
            if doc.discount_as == "Percent":
                rate = rate - (flt(doc.discount) * rate / 100)
            if doc.discount_as == "Fixed Amount":
                rate = rate - flt(doc.discount)
            return {
                "item": doc.pet_service_item,
                "rate": rate,
            }
        else:
            frappe.msgprint(_("No valid item found for the pet"))
        return {
            "item": None,
            "rate": 0,
        }


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
    DocShare = frappe.qb.DocType("DocShare")

    share_query = ExistsCriterion(
        frappe.qb.from_(DocShare)
        .select(1)
        .where(
            (DocShare.share_doctype == "Appointment")
            & (DocShare.share_name == Appointment.name)
            & (DocShare.user == user)
        )
    )
    query = (
        frappe.qb.from_(Appointment)
        .select(
            Appointment.name,
            Appointment.status,
            functions.IfNull(Appointment.custom_vehicle, "unassigned").as_(
                "resourceId"
            ),  # resourceId for calendar-view
            Appointment.custom_vehicle.as_("vehicle"),
            # Appointment.customer_details.as_("subject"),
            Concat(
                Appointment.customer_name,
                ": ",
                Appointment.customer_phone_number,
                " - ",
                Appointment.custom_subject,
                " ,for ",
                Appointment.custom_total_pets,
                " (Pets)",
            ).as_("subject"),
            Appointment.docstatus,
            Appointment.status,
            Appointment.customer_details.as_("description"),
            Appointment.custom_color.as_("color"),
            Appointment.scheduled_time.as_("scheduled_time"),
            Appointment.custom_ends_on.as_("ends_on"),
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
            & ((Appointment.owner == user) | share_query)
        )
    )
    if for_reminder:
        query = query.where(Appointment.custom_send_reminder == 1)

    appointments = query.run(as_dict=True)
    return appointments


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
