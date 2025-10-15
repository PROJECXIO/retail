# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class PetServiceItem(Document):
	def on_update(self):
		self.update_item_price()
	
	def update_item_price(self):
		exists = frappe.db.exists("Item Price", {"item_code": self.item, "uom": self.uom, "price_list": "Standard Selling"})
		if exists:
			price_doc = frappe.get_doc("Item Price", exists)
		else:
			price_doc = frappe.new_doc("Item Price")
			price_doc.update({"item_code": self.item, "uom": self.uom, "price_list": "Standard Selling"})
		price_doc.update({
			"price_list_rate": flt(self.rate)
		})
		price_doc.save(ignore_permissions=True)

