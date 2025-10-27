frappe.provide("frappe.ui.form");



frappe.provide("frappe.ui.form");

ContactAddressQuickEntryForm = class ContactAddressQuickEntryForm extends (
	frappe.ui.form.QuickEntryForm
) {
	constructor(doctype, after_insert, init_callback, doc, force) {
		super(doctype, after_insert, init_callback, doc, force);
		this.skip_redirect_on_error = true;
	}
	render_dialog() {
		this.mandatory = this.mandatory.concat(this.get_variant_fields());
		super.render_dialog();
	}
	insert() {
		/**
		 * Using alias fieldnames because the doctype definition define "email_id" and "mobile_no" as readonly fields.
		 * Therefor, resulting in the fields being "hidden".
		 */
		const map_field_names = {
			email_address: ["email_id", "custom_email_id_2"],
			mobile_number: ["mobile_no", "custom_mobile_no_2"],
		};

		Object.entries(map_field_names).forEach(([fieldname, new_fieldnames]) => {
			new_fieldnames.forEach(nf => {
			this.dialog.doc[nf] = this.dialog.doc[fieldname];
			});
			delete this.dialog.doc[fieldname];
		});

		return super.insert();
	}

	get_variant_fields() {
		var variant_fields = [
			{
				fieldtype: "Section Break",
			},
			{
				label: __("Email Id"),
				fieldname: "email_address",
				fieldtype: "Data",
				options: "Email",
			},
			{
				fieldtype: "Column Break",
			},
			{
				label: __("Mobile Number"),
				fieldname: "mobile_number",
				fieldtype: "Data",
			},
		];

		return variant_fields;
	}
};


frappe.ui.form.CustomerQuickEntryForm = ContactAddressQuickEntryForm;
