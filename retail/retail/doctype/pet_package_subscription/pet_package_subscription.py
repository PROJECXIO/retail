# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

class PetPackageSubscription(Document):
    def validate(self):
        total_amount, total_net_amount, total_qty, total_extra_qty = (
            self.check_discount_values()
        )
        self.total_amount = total_amount
        self.total_net_amount = total_net_amount
        self.total_qty = total_qty
        self.total_extra_qty = total_extra_qty
        self.total_net_qty = total_qty + total_extra_qty

        self.fetch_service_items()

    def before_submit(self):
        self.status = "Open"

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    @frappe.whitelist()
    def create_invoice(self, due_date=False, payments_details=[]):
        if self.sales_invoice or self.docstatus != 1:
            return

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.customer
        invoice.posting_date = self.subscription_at
        invoice.due_date = due_date or getdate()
        for service in self.subscription_package_service:
            if not service.service or not service.service_item:
                continue
            doc = frappe.get_doc("Pet Service Item", service.service_item)
            rate = flt(service.rate)
            discount_percentage = 0
            if flt(service.discount) > 0:
                rate = rate - (rate * flt(service.discount) / 100)
            item = {
                "item_code": doc.item,
                "uom": doc.uom,
                "qty": service.qty,
                "rate": rate,
                "discount_percentage": discount_percentage,
            }

            invoice.append(
                "items",
                item,
            )
        additional_discount = flt(self.additional_discount)
        if additional_discount > 0:
            if self.additional_discount_as == "Fixed Amount":
                invoice.discount_amount = additional_discount
            elif self.additional_discount_as == "Percent":
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
        self.db_set("sales_invoice", invoice.name)
        return "ok"
    
    def check_discount_values(self):
        total_amount = 0
        total_net_amount = 0
        total_qty = 0
        total_extra_qty = 0
        for row in self.package_services:
            row.amount = flt(row.rate) * cint(row.qty)
            total_amount += flt(row.amount)
            total_qty += cint(row.qty)
            total_extra_qty += cint(row.extra_qty)
            amount = 0
            if row.discount_as == "Percent":
                if flt(row.discount) > 100:
                    frappe.throw(
                        _(
                            "Discount Percent can not be greater than 100 at row {}"
                        ).format(row.idx)
                    )
                amount = flt(row.amount) - (flt(row.amount) * flt(row.discount)) / 100
            elif row.discount_as == "Fixed Amount":
                if flt(row.discount) > flt(row.amount):
                    frappe.throw(
                        _(
                            "Discount Amount can not be greater than {} at row {}"
                        ).format(row.amount, row.idx)
                    )
                amount = flt(row.amount) - flt(row.discount)
            else:
                amount = flt(row.amount)
            total_net_amount += amount
        if self.additional_discount_as == "Percent":
            if flt(self.additional_discount) > 100:
                frappe.throw(
                    _("Additional Discount Percent can not be greater than 100")
                )
            total_net_amount = (
                flt(total_net_amount)
                - (flt(total_net_amount) * flt(self.additional_discount)) / 100
            )
        elif self.additional_discount_as == "Fixed Amount":
            if flt(self.additional_discount) > total_net_amount:
                frappe.throw(
                    _("Additional Discount Amount can not be greater than {}").format(
                        total_net_amount
                    )
                )
            total_net_amount = flt(total_net_amount) - flt(self.additional_discount)

        return total_amount, total_net_amount, total_qty, total_extra_qty

    def fetch_service_items(self):
        self.subscription_package_service = []
        for row in self.package_services:
            package = frappe.get_doc("Pet Service Package", row.pet_service_package)
            total_qty = cint(row.qty)
            for service in package.package_services:
                qty = cint(service.qty) * total_qty
                rate = flt(service.rate)
                amount = qty * rate
                if row.discount_as == "percent":
                    amount = amount - (amount * flt(row.discount)) / 100

                self.append(
                    "subscription_package_service",
                    {
                        "service": service.service,
                        "service_item": service.service_item,
                        "qty": qty,
                        "working_hours": service.working_hours,
                        "rate": rate,
                        "amount": amount,
                        "discount": flt(row.discount),
                    },
                )
