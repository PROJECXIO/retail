# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

# import frappe
# from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
# from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


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
            row.consumed_qty = 0
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
        self.total_net_selling_amount = net_total
        self.outstanding_amount = net_total
        self.grand_total = net_total

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
