import frappe
from frappe import _, bold
from erpnext.selling.doctype.customer.customer import Customer as BaseCustomer
from retail.utils.data import normalize_mobile

class Customer(BaseCustomer):
    def before_validate(self):
        self.format_contact_details()


    def format_contact_details(self):
        if isinstance(self.custom_email_id_2, str):
            self.custom_email_id_2 = self.custom_email_id_2.lower()
        self.custom_mobile_no_2 = normalize_mobile(self.custom_mobile_no_2)

    def validate(self):
        super().validate()
        self.validate_mobile_no()
    
    def validate_mobile_no(self):
        if not self.custom_mobile_no_2:
            return
        if frappe.db.get_value("Customer", {"name": ["!=", self.name], "custom_mobile_no_2": self.custom_mobile_no_2}):
            frappe.throw(_("The mobile number {} is already registered to another customer.").format(bold(self.custom_mobile_no_2)))