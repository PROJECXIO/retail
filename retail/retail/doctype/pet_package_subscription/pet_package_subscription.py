# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

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

    def on_submit(self):
        self.update_status_field(False)

    def on_cancel(self):
        self.update_status_field(False)

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
    def create_invoice(self, due_date=False, payments_details=[]):
        if self.sales_invoice:
            frappe.msgprint(_("Invoice is created"))
            return

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.customer
        invoice.posting_date = getdate()
        invoice.due_date = getdate(due_date) if due_date else getdate()
        diff_percent1 = (flt(self.selling_amount) - flt(self.total_net_amount)) * 100 / flt(self.total_net_amount)
        if diff_percent1 != 0:
            diff_percent1 *= -1
        # Prepare items
        for package in self.package_services:
            diff_percent2 = (flt(package.selling_amount) - flt(package.total_amount)) * 100 / flt(package.total_amount)
            if diff_percent2 != 0:
                 diff_percent2 *= -1
            diff_percent3 = -1 * flt(package.discount)
            if diff_percent3 != 0:
                 diff_percent3 *= -1
            package = frappe.get_doc("Pet Service Package", package.pet_service_package)
            package_qty = cint(package.package_qty)

            for item in package.package_services:
                rate = flt(item.selling_rate)
                print(rate)
                # apply price different
                rate = rate - (rate * diff_percent1 / 100)
                rate = rate - (rate * diff_percent2 / 100)
                rate = rate - (rate * diff_percent3 / 100)
                doc = frappe.get_doc("Pet Service Item", item.service_item)
                item = {
                    "item_code": doc.item,
                    "uom": doc.uom,
                    "qty": package_qty,
                    "rate": rate,
                }
                if rate <= 0:
                    item.update({
                        "rate": 0,
                        "discount_percentage": 100,
                    })
                print(item)
                invoice.append(
                    "items",
                    item,
                )

        invoice.additional_discount = flt(self.additional_discount)
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

    def update_subscription_consuming_status(self, update_status=True):
        total = 0
        consumed = 0
        for pkg in self.package_services:
            total += cint(pkg.package_qty)
            consumed += cint(pkg.consumed_qty)
        
        if consumed == 0:
            self.db_set("consumed_status", "Not Consumed", update_modified=False)
        elif total > consumed:
            self.db_set("consumed_status", "Partly Consumed", update_modified=False)
        else:
            self.db_set("consumed_status", "Consumed", update_modified=False)
        
        if update_status:
            self.update_subscription_status()

    def update_subscription_payment_status(self, update_status=True):
        if flt(self.outstanding_amount) == 0:
            self.db_set("payment_status", "Paid", update_modified=False)
        elif  flt(self.selling_amount) > flt(self.outstanding_amount):
            self.db_set("payment_status", "Partly Paid", update_modified=False)
        else:
            self.db_set("payment_status", "Not Paid", update_modified=False)
        if update_status:
            self.update_subscription_status()

    def update_subscription_status(self):
        if self.docstatus == 0:
            self.db_set("status", "Draft", update_modified=False)
        if self.docstatus == 2:
            self.db_set("status", "Cancelled", update_modified=False)
            return
        if self.payment_status == "Paid" and self.consumed_status == "Consumed":
            self.db_set("status", "Completed", update_modified=False)
        else:
            self.db_set("status", "Active", update_modified=False)
    
    def update_status_field(self, update_status=True):
        self.update_subscription_consuming_status(update_status)
        self.update_subscription_payment_status(update_status)
        self.update_subscription_status()