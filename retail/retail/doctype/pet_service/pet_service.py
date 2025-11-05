# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PetService(Document):
    def validate(self):
        self.total_price, self.pet_type, self.pet_size = self.check_discount_values()
        if flt(self.selling_price) <= 0:
            self.selling_price = flt(self.total_price)

        self.different_price = flt(self.selling_price) - flt(self.total_price)

    def check_discount_values(self):

        type = set()
        size = set()
        total_price = 0
    
        for row in self.service_items:
            total_price += flt(row.rate)
            if row.pet_type:
                type.add(row.pet_type)
            if row.pet_size:
                size.add(row.pet_size)
        size = ", ".join(size)
        type = ", ".join(type)

        return total_price, type, size
