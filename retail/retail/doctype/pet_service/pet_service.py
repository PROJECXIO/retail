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
        if self.discount_as == "Percent" and flt(self.discount) > 100:
            frappe.throw(_("Discount Percent can not be greater that 100"))

        if self.discount_as == "Fixed Amount" and flt(self.discount) >  flt(self.total_price):
            frappe.throw(_("Discount Amount can not be greater that total price {}", [self.total_price]))

        
        total_price = 0
        for row in self.service_items:
            total_price += flt(row.rate)
        total_net_price = 0
        if(self.discount_as == "Percent"):
            total_net_price += (flt(total_price) - (flt(total_price) * flt(self.discount) / 100))
        elif(self.discount_as == "Fixed Amount"):
            total_net_price += (flt(total_price) - flt(self.discount))
        else:
            total_net_price += flt(total_price)

        return total_price, total_net_price
