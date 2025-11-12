# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class PetPackageSubscription(Document):
    def validate(self):
        self.merge_pkgs()
        self.calculate_totals()

    def calculate_totals(self):
        self.total_packages_amount = 0
        self.total_selling_amount = 0
        self.total_net_amount = 0
        self.total_working_hours = 0

        for row in self.package_services or []:
            self.total_packages_amount += flt(row.total_amount)
            self.total_selling_amount += flt(row.selling_amount)
            self.total_net_amount += (
                flt(row.selling_amount)
                - (flt(row.discount) * flt(row.selling_amount)) / 100
            )
            self.total_working_hours += flt(row.working_hours)
        if flt(self.selling_amount) <= 0:
            self.selling_amount = flt(self.total_net_amount)
        net_total = (
            flt(self.selling_amount)
            - (flt(self.additional_discount) * flt(self.selling_amount)) / 100
        )
        print(net_total)
        print(net_total)
        print(net_total)
        print(net_total)
        print(net_total)

    def before_submit(self):
        self.status = "Open"

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    def merge_pkgs(self):
        added = []
        unique_rows = []
        for p in self.package_services:
            if p.pet_service_package in added:
                continue
            unique_rows.append(p)
        self.package_services = []
        for idx, u in enumerate(unique_rows, 1):
            u.set("idx", idx)
            self.append("package_services", u)

    @frappe.whitelist()
    def create_invoice(self, due_date=False, payments_details=None):
        payments_details = payments_details or []

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.customer
        invoice.posting_date = self.subscription_at
        invoice.due_date = due_date or getdate()

        for service in self.subscription_package_service or []:
            if not service.service_item:
                continue
            item_doc = frappe.get_doc("Pet Service Item", service.service_item)

            qty = flt(service.qty)
            unit_rate = flt(service.selling_rate) if qty else flt(service.rate)

            si_item = {
                "item_code": item_doc.item,
                "uom": item_doc.uom,
                "qty": qty,
                "rate": unit_rate,
                "discount_percentage": 0,
            }
            row = invoice.append("items", si_item)
            if unit_rate <= 0:
                row.discount_percentage = 100

        additional_discount = flt(self.additional_discount)
        if additional_discount > 0:
            if self.additional_discount_as == "Fixed Amount":
                invoice.discount_amount = additional_discount
                invoice.additional_discount_percentage = 0
            elif self.additional_discount_as == "Percent":
                invoice.apply_discount_on = "Grand Total"
                invoice.additional_discount_percentage = additional_discount
                invoice.discount_amount = 0

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
