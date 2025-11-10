# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class PetPackageSubscription(Document):
    def validate(self):
        self.merge_pkgs()
        self.update_total_price()

        # self.total_amount, self.total_net_amount = self.calculate_totals_amounts()
        # if(self.selling_price <= 0):
        #     self.selling_price = self.total_net_amount
        # self.total_qty, self.total_extra_qty, self.total_net_qty = self.calculate_totals_qty()

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

        for service in (self.subscription_package_service or []):
            if not service.service_item:
                continue
            item_doc = frappe.get_doc("Pet Service Item", service.service_item)

            qty = flt(service.qty)
            unit_rate = flt(service.selling_rate) if qty else flt(service.rate)

            si_item ={
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
    def update_total_price(self):
        pkg_discounts = self.build_package_discount_map()
        self.total_packages_amount = 0.0
        self.total_selling_amount = 0.0
        self.total_net_amount = 0.0
        for r in (self.package_services or []):
            self.total_packages_amount += flt(r.package_price)
            self.total_selling_amount += flt(r.selling_rate)
            discounts = [0.0, 0.0]
            if r.pet_service_package:
                discounts = pkg_discounts[r.pet_service_package] or [0.0, 0.0]
                discount_value = flt(r.package_price) - (flt(r.package_price) * discounts[0]) / 100
            discount_value = flt(discount_value) - (discounts[1] * flt(discount_value)) / 100
            self.total_net_amount += discount_value
        total_qty = cint(self.subscription_qty)
        if flt(self.selling_rate) <= 0:
            self.selling_rate = self.total_net_amount
        selling_amount = total_qty * self.selling_rate
        net = selling_amount - (selling_amount * flt(self.additional_discount)) / 100
        self.total_net_selling_amount = net

    def compute_package_discount_factor(self, pkgRow):
        package_price = flt(pkgRow.package_price or 0)
        selling = flt(pkgRow.selling_rate or 0)
        rate_diff_discount = ((package_price - selling) / package_price) * 100.0
        pkg_discount = flt(pkgRow.discount or 0)
        return [rate_diff_discount, pkg_discount]

    def build_package_discount_map(self):
        map ={}
        for row in (self.package_services or []):
            if row.pet_service_package:
                map.update({
                    f"{row.pet_service_package}": self.compute_package_discount_factor(row)
                })
        return map