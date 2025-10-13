# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PetService(Document):
    def validate(self):
        total_price, total_net_price = self.check_discount_values()
        self.total_price = total_price
        self.total_net_price = total_net_price

    def check_discount_values(self):
        total_price = 0
        total_net_price = 0
        for item in self.service_items:
            if item.discount_as == "Percent" and flt(item.discount) > 100:
                frappe.throw(
                    _("Discount Percent at row {} can not be greater that 100").format(
                        item.idx
                    )
                )
            if item.discount_as == "Fixed Amount" and flt(item.discount) > flt(
                item.rate
            ):
                frappe.throw(
                    _(
                        "Discount Amount at row {} can not be greater that rate {}"
                    ).format(item.idx, item.rate)
                )

            total_price += flt(item.rate)
            if item.discount_as == "Percent":
                total_net_price += flt(item.rate) - (
                    flt(item.rate) * flt(item.discount) / 100
                )
            elif item.discount_as == "Fixed Amount":
                total_net_price += flt(item.rate) - flt(item.discount)
            else:
                total_net_price += flt(item.rate)

        return total_price, total_net_price
