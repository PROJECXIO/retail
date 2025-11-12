# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class AppointmentCommission(Document):
    def validate(self):
        self.validate_commissions_and_tips()

    def validate_commissions_and_tips(self):
        if cint(self.enabled) == 0:
            return
        # Validate commissions totals
        total_commissions = (
            flt(self.groomer_commission)
            + flt(self.driver_commission)
            + flt(self.other_commission)
        )
        if total_commissions > 100:
            frappe.throw(_("Total commissions % can not be greater than 100"))
        total_tips = (
            flt(self.groomer_tips) + flt(self.driver_tips) + flt(self.other_tips)
        )
        if total_tips > 100:
            frappe.throw(_("Total tips % can not be greater than 100"))
