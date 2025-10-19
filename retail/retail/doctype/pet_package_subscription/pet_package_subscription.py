# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint

class PetPackageSubscription(Document):
	def validate(self):
		total_amount, total_net_amount, total_qty, total_extra_qty = self.check_discount_values()
		self.total_amount = total_amount
		self.total_net_amount = total_net_amount
		self.total_qty = total_qty
		self.total_extra_qty = total_extra_qty
		self.total_net_qty = total_qty + total_extra_qty

		self.fetch_service_items()

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
					frappe.throw(_("Discount Percent can not be greater than 100 at row {}").format(row.idx))
				amount = flt(row.amount) - (flt(row.amount) * flt(row.discount)) / 100
			elif row.discount_as == "Fixed Amount":
				if flt(row.discount) > flt(row.amount):
					frappe.throw(_("Discount Amount can not be greater than {} at row {}").format(row.amount, row.idx))
				amount = flt(row.amount) - flt(row.discount)
			else:
				amount = flt(row.amount)
			total_net_amount += amount
		if self.additional_discount_as == "Percent":
			if flt(self.additional_discount) > 100:
					frappe.throw(_("Additional Discount Percent can not be greater than 100"))
			total_net_amount = flt(total_net_amount) - (flt(total_net_amount) * flt(self.additional_discount)) / 100
		elif self.additional_discount_as == "Fixed Amount":
			if flt(self.additional_discount) > total_net_amount:
					frappe.throw(_("Additional Discount Amount can not be greater than {}").format(total_net_amount))
			total_net_amount = flt(total_net_amount) - flt(self.additional_discount)
    
		return total_amount, total_net_amount, total_qty, total_extra_qty

	def fetch_service_items(self):
		self.subscription_package_service = []
		for row in self.package_services:
			package = frappe.get_doc("Pet Service Package", row.pet_service_package)
			total_qty = cint(row.qty)		
			for service in package.package_services:
				qty = cint(service.qty) * total_qty
				rate = flt(service.rate)
				amount = qty * rate
				if row.discount_as == "percent":
					amount = amount - (amount * flt(row.discount)) / 100
				
				self.append("subscription_package_service", {
					"service": service.service,
					"service_item": service.service_item,
					"qty": qty,
					"working_hours": service.working_hours,
					"rate": rate,
					"amount": amount,
				})
