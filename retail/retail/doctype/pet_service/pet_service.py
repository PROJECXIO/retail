# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import flt

class PetService(Document):
	def validate(self):
		self.total_price = 0
		self.total_net_price = 0
		for item in self.service_items:
			self.total_price += flt(item.rate)
			if item.discount_as == "Percent":
				self.total_net_price += (flt(item.rate) - (flt(item.rate) * flt(item.discount) / 100));
			elif item.discount_as == "Fixed Amount":
				self.total_net_price += (flt(item.rate) - flt(item.discount));
			else:
				self.total_net_price += flt(item.rate);

