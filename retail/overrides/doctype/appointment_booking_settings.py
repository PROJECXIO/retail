import frappe
from frappe.utils import cint

from erpnext.crm.doctype.appointment_booking_settings.appointment_booking_settings import (
    AppointmentBookingSettings as BaseAppointmentBookingSettings,
)


class AppointmentBookingSettings(BaseAppointmentBookingSettings):
    def on_update(self):
        self.update_read_only_for_ends_time()

    def update_read_only_for_ends_time(self):
        prev_doc = self.get_doc_before_save()
        if cint(prev_doc.custom_allow_to_update_appointment_end_time) == cint(
            self.custom_allow_to_update_appointment_end_time
        ):
            return
        exists = frappe.db.exists(
            "Property Setter",
            {
                "doctype_or_field": "DocField",
                "doc_type": "Appointment",
                "field_name": "custom_ends_on",
                "property_type": "Check",
                "property": "read_only",
            },
        )

        if exists:
            doc = frappe.get_doc("Property Setter", exists)
        else:
            doc = frappe.new_doc("Property Setter")
            doc.update(
                {
                    "doctype_or_field": "DocField",
                    "doc_type": "Appointment",
                    "field_name": "custom_ends_on",
                    "property_type": "Check",
                    "property": "read_only",
                }
            )
        doc.update(
            {
                "value": (
                    "0"
                    if cint(self.custom_allow_to_update_appointment_end_time)
                    else "1"
                ),
            }
        )
        doc.save(ignore_permissions=True)
