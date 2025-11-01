import frappe

def execute():
    template = frappe.db.get_single_value("Appointment Booking Settings", "custom_booking_template_message") or ""
    if not template:
        return
    for a in frappe.db.sql("SELECT name FROM `tabAppointment` WHERE docstatus!=2"):
        a = frappe.get_doc("Appointment", a[0])
        context = a.as_dict()
        pets_services = []
        for row in a.custom_appointment_services:
            pet_name = frappe.db.get_value("Pet", row.pet, "pet_name")
            pets_services.append(f"{pet_name} - {row.service}")
        pets_services = "\n".join(pets_services)
        context.update({
            "pets_services": pets_services,
        })
        template_message = frappe.render_template(template, context=context)
        frappe.db.set_value("Appointment", a.name, "custom_appointment_message", template_message, update_modified=False)
    frappe.db.commit()
