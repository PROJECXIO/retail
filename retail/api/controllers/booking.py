from retail.api.utils.endpoints import create_doc
import frappe

def create_booking():
    doctype = "CRM Lead"

    full_name = frappe.form_dict.get("full_name")
    first_name = full_name.split(" ")[0]
    last_name = " ".join(full_name.split(" ")[1:]) or "."
    msg = frappe.form_dict.get("message") or ""

    if frappe.form_dict.get("check_in_date"):
        msg += f"\nCheck-in: {frappe.form_dict.get('check_in_date')}"

    if frappe.form_dict.get("check_out_date"):
        msg += f"\nCheck-out: {frappe.form_dict.get('check_out_date')}"

    booking_data = {
        "lead_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "email_id": frappe.form_dict.get("email"),
        "phone": frappe.form_dict.get("phone") or frappe.form_dict.get("phone_number"),
        "source": "Website Booking",
        "service": frappe.form_dict.get("service"),
        "message": msg.strip(),
    }

    create_doc(doctype, booking_data, ignore_permissions=True)
