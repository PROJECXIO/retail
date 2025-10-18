frappe.ui.form.on("Appointment", {
    onload(frm) {
        frm.set_query("pet", "custom_appointment_services", function (doc) {
            return {
                filters: {
                    customer: doc.party,
                },
            };
        });
        frm.set_query(
            "service",
            "custom_appointment_services",
            function (doc, cdt, cdn) {
                const row = locals[cdt][cdn];
                return {
                    filters: {
                        pet_type: row.pet_type,
                        pet_size: row.pet_size,
                    },
                    query:
                        "retail.retail.doctype.pet_service_package.pet_service_package.service_query",
                };
            }
        );
    },
    refresh(frm) {
        frm.trigger("set_label");
        if (frm.doc.docstatus == 1 && frm.doc.status == "Open") {
            frm.add_custom_button(
                __("Complete Appointment"),
                () => {
                    const table_fields = [
                        {
                            fieldname: "mode_of_payment",
                            fieldtype: "Link",
                            in_list_view: 1,
                            label: __("Mode of Payment"),
                            options: "Mode of Payment",
                            reqd: 1,
                        },
                        {
                            fieldname: "paid_amount",
                            fieldtype: "Currency",
                            in_list_view: 1,
                            label: __("Paid Amount"),
                            options: "company:company_currency",
                            onchange: function () {
                                dialog.fields_dict.payments_details.df.data.some((d) => {
                                    if (d.idx == this.doc.idx) {
                                        d.paid_amount = this.value;
                                        dialog.fields_dict.payments_details.grid.refresh();
                                        return true;
                                    }
                                });
                            },
                        },
                    ];
                    let dialog = new frappe.ui.Dialog({
                        title: __("Complete Appointment"),
                        fields: [
                            {
                                fieldtype: "HTML",
                                fieldname: "info_message",
                                options: `
                                    <div style="padding:16px 0; color:#666;">
                                        ${__(
                                    "Are you sure you want to complete the appointment?"
                                )}
                                    </div>
                                `,
                            },
                            {
                                label: __("Update Ends time"),
                                fieldtype: "Check",
                                fieldname: "update_ends_time",
                            },
                            {
                                fieldname: "payments_details",
                                fieldtype: "Table",
                                label: __("Customer Payments"),
                                cannot_add_rows: false,
                                in_place_edit: true,
                                data: [],
                                fields: table_fields,
                            },
                        ],
                        primary_action(data) {
                            frappe.call({
                                method: "create_invoice_appointment",
                                doc: frm.doc,
                                args: data,
                                callback: function (r) {
                                    frm.reload_doc();
                                },
                            });
                            dialog.hide();
                        },
                        primary_action_label: __("Complete Appointment"),
                    });
                    dialog.show();
                },
                __("Action")
            );
            frm.add_custom_button(
                __("Close Appointment"),
                () => {
                    frappe.confirm(
                        __("Are you sure you want to close the appointment?"),
                        () => {
                            frappe.call({
                                method: "close_appointment",
                                doc: frm.doc,
                                callback: function (r) {
                                    frm.reload_doc();
                                },
                            });
                        }
                    );
                },
                __("Action")
            );
        }
        if (frm.doc.docstatus == 1 && frm.doc.status == "Closed") {
            frm
                .add_custom_button(__("Re-Open"), () => {
                    frappe.call({
                        method: "re_open_appointment",
                        doc: frm.doc,
                        callback: function (r) {
                            frm.reload_doc();
                        },
                    });
                })
                .addClass("btn-primary")
                .removeClass("btn-default");
        }
    },
    appointment_with(frm) {
        frm.trigger("set_label");
        frm.set_value("party", "");
    },
    async party(frm) {
        if (!frm.doc.appointment_with || !frm.doc.party) {
            await frm.set_value("customer_name", "");
            await frm.set_value("customer_phone_number", "");
            await frm.set_value("customer_email", "");
            await frm.set_value("custom_address", "");
        } else {
            if (frm.doc.appointment_with == "Customer") {
                let pin_location = await frappe.db.get_value(
                    "Customer",
                    frm.doc.party,
                    "custom_pin_location"
                );
                pin_location =
                    pin_location && pin_location.message && pin_location.message.custom_pin_location;

                let mobile_no = await frappe.db.get_value(
                    "Customer",
                    frm.doc.party,
                    "mobile_no"
                );
                mobile_no =
                    mobile_no && mobile_no.message && mobile_no.message.mobile_no;
                let customer_name = await frappe.db.get_value(
                    "Customer",
                    frm.doc.party,
                    "customer_name"
                );
                customer_name =
                    customer_name &&
                    customer_name.message &&
                    customer_name.message.customer_name;
                let primary_address = await frappe.db.get_value(
                    "Customer",
                    frm.doc.party,
                    "primary_address"
                );
                primary_address =
                    (primary_address &&
                        primary_address.message &&
                        primary_address.message.primary_address) ||
                    "";
                primary_address = primary_address.replaceAll("<br>", "");
                await frm.set_value("customer_name", customer_name);
                await frm.set_value("customer_phone_number", mobile_no);
                await frm.set_value("custom_address", primary_address);
                await frm.set_value("custom_appointment_location", pin_location);
            }
        }
    },
    set_label(frm) {
        frm.set_df_property(
            "party",
            "label",
            __(frm.doc.appointment_with) || __("Party")
        );
        frm.set_df_property(
            "customer_name",
            "label",
            __(`${frm.doc.appointment_with} Name`) || __("Party Name")
        );
    },
    custom_additional_discount_as(frm){
        frm.trigger("update_total_price");
    },
    custom_additional_discount(frm){
        frm.trigger("update_total_price");
    },
    update_total_price(frm) {
        let total_price = 0;
        let total_net_price = 0;
        (frm.doc.custom_appointment_services || []).forEach(row => {
            total_price += flt(row.price);
            let amount = 0;
            if (row.discount_as == "Percent") {
                amount = flt(row.price) - (flt(row.price) * flt(row.discount)) / 100;
            } else if (row.discount_as == "Fixed Amount") {
                amount = flt(row.price) - flt(row.discount);
            } else {
                amount = flt(row.price);
            }
            total_net_price += amount;
        });

        if (frm.doc.custom_additional_discount_as == "Percent") {
            total_net_price =
                flt(total_net_price) - (flt(total_net_price) * flt(frm.doc.custom_additional_discount)) / 100;
        } else if (frm.doc.custom_additional_discount_as == "Fixed Amount") {
            total_net_price = flt(total_net_price) - flt(frm.doc.custom_additional_discount);
        }

        frm.set_value("custom_total_amount", total_price);
        frm.refresh_field("custom_total_amount");

        frm.set_value("custom_total_net_amount", total_net_price);
        frm.refresh_field("custom_total_net_amount");
    },
});

frappe.ui.form.on("Appointment Service", {
    custom_appointment_services_remove(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
    pet(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.service = null;
        row.service_item = null;
        row.price = 0;
        frm.trigger("update_total_price");
    },
    price(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
    discount_as(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
    discount(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
    async service(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.service) {
            frappe.call({
                method: "fetch_service_item",
                doc: frm.doc,
                args: {
                    service: row.service,
                    pet_type: row.pet_type,
                    pet_size: row.pet_size,
                },
                callback: function(r){
                    row.service_item = r.message && r.message.item || '';
                    row.price = r.message && r.message.rate || 0;
                    frm.refresh_field("custom_appointment_services");
                    frm.trigger("update_total_price");
                },
                freeze: true,
            });
        }else{
            row.service_item = null;
            frm.trigger("update_total_price");
        }
    },
});
