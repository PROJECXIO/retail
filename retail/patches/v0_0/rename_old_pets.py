import frappe
from frappe.model.naming import make_autoname


def execute():
    for p in frappe.db.sql("SELECT name FROM `tabPet` WHERE name not like 'PEt-%'"):
        frappe.rename_doc("Pet", p[0], make_autoname("PET-.###"), force=True)
        frappe.db.commit()
