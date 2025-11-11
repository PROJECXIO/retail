import frappe


def execute():
    for c in frappe.db.sql("SELECT name, customer_name FROM `tabCustomer`"):
        name = c[0]
        customer_name = c[1]
        frappe.db.set_value("Customer", name, "custom_first_name", customer_name)
    frappe.db.commit()
