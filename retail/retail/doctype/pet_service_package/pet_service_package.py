# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, unique
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond, get_match_cond

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

# searches for valid services
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def service_query(doctype, txt, searchfield, start, page_len, filters):
	item_fields = get_fields(doctype, ["name", "pet_type", "pet_size"])
	item_filters = {}
	item_filters.update(filters)
	valid_items = frappe.db.sql(
		"""select {fields} from `tabPet Service Item`
		where docstatus < 2
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			idx desc,
			name
		limit %(page_len)s offset %(start)s""".format(
			**{
				"fields": ", ".join(item_fields),
				"fcond": get_filters_cond("Pet Service Item", item_filters, []),
				"mcond": get_match_cond("Pet Service Item"),
			}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
		pluck="name",
	)
	if len(valid_items) == 0:
		return []
	valid_items = ", ".join([f"'{i}'" for i in valid_items])
	valid_services = frappe.db.sql("SELECT DISTINCT(parent) FROM `tabPet Service Item Detail` WHERE pet_service_item IN ({})".format(valid_items), pluck="name",)
	if len(valid_services) == 0:
		return []

	doctype = "Pet Service"
	conditions = []
	fields = get_fields(doctype, ["name", "total_net_price"])
	filters = {
		"name": ["in", valid_services]
	}
	return frappe.db.sql(
		"""select name, CONCAT('Rate ', ROUND(total_net_price, 3)) from `tabPet Service`
		where docstatus < 2
			and ({key} like %(txt)s
				or name like %(txt)s)
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			idx desc,
			name
		limit %(page_len)s offset %(start)s""".format(
			**{
				"fields": ", ".join(fields),
				"key": searchfield,
				"fcond": get_filters_cond(doctype, filters, conditions),
				"mcond": get_match_cond(doctype),
			}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
	)

def get_fields(doctype, fields=None):
	if fields is None:
		fields = []
	meta = frappe.get_meta(doctype)
	fields.extend(meta.get_search_fields())

	if meta.title_field and meta.title_field.strip() not in fields:
		fields.insert(1, meta.title_field.strip())

	return unique(fields)
