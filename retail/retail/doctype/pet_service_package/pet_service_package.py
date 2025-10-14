# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.model.document import Document


class PetServicePackage(Document):
	def validate(self):
		(
			self.total_package_price,
			self.net_total_package_price,
			self.total_package_qty,
		) = self.check_discount_values()

	def check_discount_values(self):
		total_price = 0
		total_net_price = 0
		total_qty = 0

		for row in self.package_services:
			total_qty += cint(row.qty)

			total_price += flt(row.rate)
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

		return total_price, total_net_price, total_qty

