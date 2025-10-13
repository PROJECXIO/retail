# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint


class CustomerServicePackage(Document):
    def validate(self):
        (
            self.total_package_price,
            self.net_total_package_price,
            self.total_package_qty,
            self.total_extra_qty,
        ) = self.check_discount_values()
        self.net_total_qty = cint(self.total_package_qty) + cint(self.total_extra_qty)

    def check_discount_values(self):
        total_price = 0
        total_net_price = 0
        total_qty = 0
        total_extra_qty = 0

        for row in self.package_services:
            if row.discount_as == "Percent" and flt(row.discount) > 100:
                frappe.throw(
                    _("Discount Percent at row {} can not be greater that 100").format(
                        row.idx
                    )
                )
            if row.discount_as == "Fixed Amount" and flt(row.discount) > flt(row.rate):
                frappe.throw(
                    _(
                        "Discount Amount at row {} can not be greater that rate {}"
                    ).format(row.idx, row.rate)
                )

            total_qty += cint(row.qty)
            total_extra_qty += cint(row.extra_qty)

            total_price += flt(row.rate)
            if row.discount_as == "Percent":
                total_net_price += flt(row.rate) - (
                    flt(row.rate) * flt(row.discount) / 100
                )
            elif row.discount_as == "Fixed Amount":
                total_net_price += flt(row.rate) - flt(row.discount)
            else:
                total_net_price += flt(row.rate)
        if self.additional_discount_as == "Percent":
            if flt(self.additional_discount) > 100:
                frappe.throw(
                    _("Additional Discount Percent can not be greater that 100")
                )
            total_net_price = (
                total_net_price
                - (total_net_price * flt(self.additional_discount)) / 100
            )
        elif self.additional_discount_as == "Fixed Amount":
            if flt(self.additional_discount) > total_net_price:
                frappe.throw(
                    _(
                        "Additional Discount Amount can not be greater that rate {}"
                    ).format(total_net_price)
                )
            total_net_price = total_net_price - flt(self.additional_discount)

        return total_price, total_net_price, total_qty, total_extra_qty
