# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PetService(Document):
    def validate(self):
        self.pet_type, self.pet_size = self.update_pet_specifications()

    def update_pet_specifications(self):

        type = set()
        size = set()

        for row in self.service_items:
            if row.pet_type:
                type.add(row.pet_type)
            if row.pet_size:
                size.add(row.pet_size)
        size = ", ".join(size)
        type = ", ".join(type)

        return type, size
