import frappe
from retail.utils.data import normalize_mobile


def execute():
    for c in frappe.db.sql(
        "SELECT name, mobile_no, email_id, custom_mobile_no_2, custom_email_id_2 FROM `tabCustomer`"
    ):
        name = c[0]
        mobile_no = c[1]
        email_id = c[2]
        mobile_no_2 = c[3]
        email_id_2 = c[4]

        if mobile_no and not mobile_no_2:
            frappe.db.set_value(
                "Customer", name, "custom_mobile_no_2", normalize_mobile(mobile_no)
            )
        if email_id and not email_id_2:
            frappe.db.set_value("Customer", name, "custom_email_id_2", email_id.lower())
    frappe.db.commit()
