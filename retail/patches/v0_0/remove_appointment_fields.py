import frappe


def execute():
    fields = [
        "custom_employee",
        "custom_employee_name",
        "custom_groomer",
        "custom_groomer_name",
        "custom_column_break_8hit2",
        "custom_column_break_snn4o",
    ]
    for field in fields:
        frappe.delete_doc_if_exists("Custom Field", f"Appointment-{field}")
    frappe.db.commit()
