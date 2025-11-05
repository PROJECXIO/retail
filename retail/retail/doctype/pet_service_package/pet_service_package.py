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
            self.total_package_qty,
            self.total_working_hours,
        ) = self.check_discount_values()

    def check_discount_values(self):
        total_price = 0
        total_qty = 0
        total_hours = 0

        for row in self.package_services:
            row.amount = flt(row.rate) * cint(row.qty)
            total_qty += cint(row.qty)
            total_price += flt(row.amount)
            total_hours += flt(row.working_hours)

        return total_price, total_qty, total_hours


# searches for valid services
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def service_query(doctype, txt, searchfield, start, page_len, filters):
    pet_type = filters.get("pet_type")
    pet_size = filters.get("pet_size")

    valid_items_both = set()
    valid_items_type_only = set()
    valid_items_size_only = set()
    
    if pet_type and pet_size:
        valid_items_both = set(
            frappe.db.sql(
                """
                SELECT DISTINCT t1.parent
                FROM `tabPet Service Item Type` t1
                INNER JOIN `tabPet Service Item Size` t2 ON t1.parent = t2.parent
                WHERE t1.pet_type = %(pet_type)s
                AND t2.pet_size = %(pet_size)s
                """,
                {"pet_type": pet_type, "pet_size": pet_size},
                pluck="parent",
            )
        )
    if pet_type:
        valid_items_type_only = set(
            frappe.db.sql(
                """
                SELECT DISTINCT t1.parent
                FROM `tabPet Service Item Type` t1
                LEFT JOIN `tabPet Service Item Size` t2 ON t1.parent = t2.parent
                WHERE t1.pet_type = %(pet_type)s
                AND (t2.pet_size IS NULL OR t2.pet_size = '')
                """,
                {"pet_type": pet_type},
                pluck="parent",
            )
        )
    if pet_size:
        valid_items_size_only = set(
            frappe.db.sql(
                """
                SELECT DISTINCT t2.parent
                FROM `tabPet Service Item Size` t2
                LEFT JOIN `tabPet Service Item Type` t1 ON t1.parent = t2.parent
                WHERE t2.pet_size = %(pet_size)s
                AND (t1.pet_type IS NULL OR t1.pet_type = '')
                """,
                {"pet_size": pet_size},
                pluck="parent",
            )
        )
    
    valid_items = valid_items_both | valid_items_type_only | valid_items_size_only
    if len(valid_items) == 0:
        return []
    valid_items = ", ".join([f"'{i}'" for i in valid_items])
    valid_services = frappe.db.sql(
        "SELECT DISTINCT(parent) FROM `tabPet Service Item Detail` WHERE pet_service_item IN ({})".format(
            valid_items
        ),
        pluck="parent",
    )
    if len(valid_services) == 0:
        return []

    doctype = "Pet Service"
    conditions = []
    filters = {"name": ["in", valid_services]}
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
                "key": searchfield,
                "fcond": get_filters_cond(doctype, filters, conditions),
                "mcond": get_match_cond(doctype),
            }
        ),
        {
            "txt": "%%%s%%" % txt,
            "_txt": txt.replace("%", ""),
            "start": start,
            "page_len": page_len,
        },
    )


# searches for valid services items
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def service_item_query(doctype, txt, searchfield, start, page_len, filters):
    item_fields = get_fields(doctype, ["pet_service_item"])
    item_filters = {}
    if "service" in filters:
        item_filters.update(
            {
                "parent": filters.get("service"),
            }
        )

    valid_items_in_service = frappe.db.sql(
        """select DISTINCT(pet_service_item) from `tabPet Service Item Detail`
		where docstatus < 2
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, pet_service_item) > 0 then locate(%(_txt)s, pet_service_item) else 99999 end),
			idx desc,
			pet_service_item
		limit %(page_len)s offset %(start)s""".format(
            **{
                "fields": ", ".join(item_fields),
                "fcond": get_filters_cond("Pet Service Item Detail", item_filters, [], ignore_permissions=True),
                "mcond": get_match_cond("Pet Service Item Detail"),
            }
        ),
        {
            "txt": "%%%s%%" % txt,
            "_txt": txt.replace("%", ""),
            "start": start,
            "page_len": page_len,
        },
        pluck="pet_service_item",
    )
    if len(valid_items_in_service) == 0:
        return []

    doctype = "Pet Service Item"
    conditions = []
    fields = get_fields(doctype, ["name", "rate"])
    filters = {"name": ["in", valid_items_in_service]}
    return frappe.db.sql(
        """select name, CONCAT('Rate ', ROUND(rate, 3)) from `tabPet Service Item`
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
        {
            "txt": "%%%s%%" % txt,
            "_txt": txt.replace("%", ""),
            "start": start,
            "page_len": page_len,
        },
    )


def get_fields(doctype, fields=None):
    if fields is None:
        fields = []
    meta = frappe.get_meta(doctype)
    fields.extend(meta.get_search_fields())

    if meta.title_field and meta.title_field.strip() not in fields:
        fields.insert(1, meta.title_field.strip())

    return unique(fields)
