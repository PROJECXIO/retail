# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PetService(Document):
    def validate(self):
        total_price, total_net_price, type, size = self.check_discount_values()
        self.total_price = total_price
        self.total_net_price = total_net_price
        self.pet_type = type
        self.pet_size = size

    def check_discount_values(self):

        type = set()
        size = set()
        total_price = 0
        total_net_price = 0
        for row in self.service_items:
            total_price += flt(row.rate)
            amount = 0
            if row.discount_as == "Percent":
                if flt(row.discount) > 100:
                    frappe.throw(_("Discount Percent can not be greater than 100 at row {}").format(row.idx))
                amount = flt(row.rate) - (flt(row.rate) * flt(row.discount)) / 100
            elif row.discount_as == "Fixed Amount":
                if flt(row.discount) > flt(row.rate):
                    frappe.throw(_("Discount Amount can not be greater than {} at row {}").format(row.rate, row.idx))
                amount = flt(row.rate) - flt(row.discount)
            else:
                amount = flt(row.rate)
            total_net_price += amount
            if row.pet_type:
                type.add(row.pet_type)
            if row.pet_size:
                size.add(row.pet_size)
        size = ", ".join(size)

        return total_price, total_net_price, type, size
