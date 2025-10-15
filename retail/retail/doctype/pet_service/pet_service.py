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
        if self.discount_as == "Percent" and flt(self.discount) > 100:
            frappe.throw(_("Discount Percent can not be greater that 100"))
        type = set()
        size = set()
        total_price = 0
        total_net_price = 0
        for row in self.service_items:
            total_price += flt(row.rate)
            amount = 0
            if row.discount_as == "Percent":
                amount = flt(row.rate) - (flt(row.rate) * flt(row.discount)) / 100
            elif row.discount_as == "Fixed Amount":
                amount = flt(row.rate) - flt(row.discount)
            else:
                amount = flt(row.rate)
            total_net_price += amount
            if row.pet_type:
                type.add(row.pet_type)
            if row.pet_size:
                size.add(row.pet_size)
        if self.discount_as == "Fixed Amount" and flt(self.discount) >  flt(total_net_price):
            frappe.throw(_("Discount Amount can not be greater that total price {}".format(total_net_price)))
        type = ", ".join(type)
        size = ", ".join(size)
        if self.discount_as == "Percent":
            total_net_price = flt(total_net_price) - (flt(total_net_price) * flt(self.discount)) / 100
        elif self.discount_as == "Fixed Amount":
            total_net_price = flt(total_net_price) - flt(self.discount)

        return total_price, total_net_price, type, size
