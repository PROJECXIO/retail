# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class PetPackageSubscription(Document):
    def validate(self):
        self.total_amount, self.total_net_amount = (
            self.calculate_totals_amounts()
        )
        self.total_qty, self.total_extra_qty, self.total_net_qty = (
            self.calculate_totals_qty()
        )

    def before_submit(self):
        self.status = "Open"

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    @frappe.whitelist()
    def create_invoice(self, due_date=False, payments_details=[]):
        # if self.sales_invoice or self.docstatus != 1:
        #     return
        pkg_discount = self.build_package_discount_map()

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = self.customer
        invoice.posting_date = self.subscription_at
        invoice.due_date = due_date or getdate()
        for service in self.subscription_package_service:
            doc = frappe.get_doc("Pet Service Item", service.service_item)
            rate = flt(service.rate)
            pkg_percent = flt(pkg_discount[service.service_package] or 0)
            # pkg discount
            rate = rate - (rate * flt(pkg_percent) / 100)
            # line discount
            rate = rate - (rate * flt(service.discount) / 100)
            item = {
                "item_code": doc.item,
                "uom": doc.uom,
                "qty": service.qty,
                "rate": rate,
            }
            item = invoice.append("items", item)
            item.rate = rate
            if rate <= 0:
                item.discount_percentage = 100

        additional_discount = flt(self.additional_discount)
        if additional_discount > 0:
            if self.additional_discount_as == "Fixed Amount":
                invoice.discount_amount = additional_discount
                invoice.additional_discount_percentage = 0
            elif self.additional_discount_as == "Percent":
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
    
    def calculate_totals_amounts(self):
        pkg_discount = self.build_package_discount_map()

        total_price = 0.0
        total_net = 0.0

        for r in (self.subscription_package_service or []):
            qty = flt(r.qty)
            rate = flt(r.rate)
            line_total = qty * rate

            pkg_percent = flt(pkg_discount[r.service_package] or 0)
            item_percent = flt(r.discount or 0)

            after_pkg = line_total * (1 - pkg_percent / 100.0)
            net = after_pkg * (1 - item_percent / 100.0)

            r.amount = net

            total_price += line_total
            total_net += net

        if self.additional_discount_as == "Percent":
            total_net = flt(total_net) - (flt(total_net) * flt(self.additional_discount)) / 100
        elif self.additional_discount_as == "Fixed Amount":
            total_net = flt(total_net) - flt(self.additional_discount)
        return total_price, total_net

    def calculate_totals_qty(self):
        total_qty = 0
        total_extra_qty = 0

        for row in (self.package_services or []):
            total_qty += cint(row.qty)
            total_extra_qty += cint(row.extra_qty)

        total_net_qty = total_qty + total_extra_qty
        return total_qty, total_extra_qty, total_net_qty

    def build_package_discount_map(self):
        map = {}
        for row in (self.package_services or []):
            if (row.pet_service_package):
                map[row.pet_service_package] = flt(row.discount or 0)
        return map
