# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt
from datetime import datetime

# import frappe
from frappe.model.document import Document


class Pet(Document):
	def validate(self):
		if len(self.pet_vaccinations) == 0:
			return
		vaccine_exp_dates = sorted([pv.expiration_date for pv in self.pet_vaccinations if pv.expiration_date], key=lambda d: datetime.strptime(d, "%Y-%m-%d"))
		if len(vaccine_exp_dates) == 0:
			return
		self.last_vaccine_exp_date = vaccine_exp_dates[-1]
