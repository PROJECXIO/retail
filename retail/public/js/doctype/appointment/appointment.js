frappe.ui.form.on("Appointment", {
    onload(frm) {
        $(document).ready(function () {
            let breadcrumbs = $("#navbar-breadcrumbs");
            breadcrumbs.find("a").first().text("Pets");
            breadcrumbs.find("a").first().attr("href", "/app/pets");
        });
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
        frm.set_query(
            "service_item",
            "custom_appointment_services",
            function (doc, cdt, cdn) {
                const row = locals[cdt][cdn];
                return {
                    filters: {
                        service: row.service,
                    },
                    query:
                        "retail.retail.doctype.pet_service_package.pet_service_package.service_item_query",
                };
            }
        );
    },
    refresh(frm) {
        frm.trigger("set_label");
        frm.trigger("add_close_btn");
        frm.trigger("add_reopen_btn");
        if (frm.doc.status !== "Completed" && !frm.doc.custom_sales_invoice) {
            frm.trigger("add_create_invoice_btn");
        }
    },
    add_close_btn(frm) {
        if (frm.doc.docstatus == 1 && frm.doc.status == "Open") {
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
    },
    add_reopen_btn(frm) {
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
    add_create_invoice_btn(frm) {
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
                            label: __("Invoice Due date"),
                            fieldtype: "Date",
                            fieldname: "due_date",
                            default: frappe.datetime.nowdate(),
                            reqd: 1,
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
                        {
                            fieldname: "tip_amount",
                            fieldtype: "Currency",
                            in_list_view: 1,
                            label: __("Tip received"),
                            options: "company:company_currency",
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
    },
    custom_vehicle(frm) {
        frappe.call({
            method: "set_vehicle_employees",
            doc: frm.doc,
            args: {
                vehicle: frm.doc.custom_vehicle || null,
            },
            callback: function (r) {
                frm.clear_table("custom_vehicle_assignment_employees");
                (r.message || []).forEach((v) => {
                    frm.add_child("custom_vehicle_assignment_employees", v);
                });
                frm.refresh_field("custom_vehicle_assignment_employees");
            },
        });
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
                let google_maps_link = await frappe.db.get_value(
                    "Customer",
                    frm.doc.party,
                    "custom_google_maps_link"
                );
                google_maps_link =
                    google_maps_link &&
                    google_maps_link.message &&
                    google_maps_link.message.custom_google_maps_link;

                let pin_location = await frappe.db.get_value(
                    "Customer",
                    frm.doc.party,
                    "custom_pin_location"
                );
                pin_location =
                    pin_location &&
                    pin_location.message &&
                    pin_location.message.custom_pin_location;

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
                    "custom_address_line"
                );
                primary_address =
                    primary_address &&
                    primary_address.message &&
                    primary_address.message.custom_address_line;
                await frm.set_value("customer_name", customer_name);
                await frm.set_value("customer_phone_number", mobile_no);
                await frm.set_value("custom_address", primary_address);
                await frm.set_value("custom_appointment_location", pin_location);
                await frm.set_value("custom_google_maps_link", google_maps_link);
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
    custom_additional_discount_as(frm) {
        frm.trigger("update_total_price");
    },
    custom_additional_discount(frm) {
        frm.trigger("update_total_price");
    },
    update_total_pets(frm) {
        const total_pets = new Set(
            (frm.doc.custom_appointment_services || [])
                .map((row) => row.pet)
                .filter((v) => v)
        ).size;
        frm.set_value("custom_total_pets", total_pets);
        frm.refresh_field("custom_total_pets");
    },
    update_total_price(frm) {
        let total_price = 0;
        let total_net_price = 0;
        let total_amount_to_pay = 0;
        let total_working_hours = 0;
        (frm.doc.custom_appointment_addons || []).forEach((row) => {
            total_price += flt(row.rate);
            total_net_price += flt(row.rate);
            total_amount_to_pay += flt(row.rate);
        });
        (frm.doc.custom_appointment_services || []).forEach((row) => {
            price = flt(row.price);
            total_price += price;
            total_net_price += price;
            if (!row.subscription) {
                total_amount_to_pay += flt(row.price);
            }
            total_working_hours += cint(row.working_hours);
        });

        if (frm.doc.custom_additional_discount_as == "Percent") {
            total_net_price =
                flt(total_net_price) -
                (flt(total_net_price) * flt(frm.doc.custom_additional_discount)) / 100;
            total_amount_to_pay =
                flt(total_amount_to_pay) -
                (flt(total_amount_to_pay) * flt(frm.doc.custom_additional_discount)) /
                100;
        } else if (frm.doc.custom_additional_discount_as == "Fixed Amount") {
            total_net_price =
                flt(total_net_price) - flt(frm.doc.custom_additional_discount);
            total_amount_to_pay =
                flt(total_amount_to_pay) - flt(frm.doc.custom_additional_discount);
        }

        frm.set_value("custom_total_amount", total_price);
        frm.set_value("custom_total_net_amount", total_net_price);
        frm.set_value("custom_total_amount_to_pay", total_amount_to_pay);
        frm.set_value("custom_total_working_hours", total_working_hours);
        frm.refresh_fields([
            "custom_total_amount",
            "custom_total_net_amount",
            "custom_total_amount_to_pay",
            "custom_total_working_hours",
        ]);
    },
    custom_send(frm) {
        let mobile = frm.doc.customer_phone_number || "";
        if (!mobile) {
            return;
        }
        if (!mobile.startsWith("+971") && !mobile.startsWith("00971")) {
            mobile = "+971" + mobile;
        }
        let url = `https://wa.me/${mobile}?text=${frm.doc.custom_appointment_message}`;
        window.open(url, "_blank");
    },
});

frappe.ui.form.on("Appointment Service", {
    custom_appointment_services_remove(frm, cdt, cdn) {
        frm.trigger("update_total_price");
        frm.trigger("update_total_pets");
    },
    pet(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.service = null;
        row.service_item = null;
        row.price = 0;
        frm.trigger("update_total_price");
        frm.trigger("update_total_pets");
    },
    price(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    discount_as(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    discount(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    async service(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.service && row.pet) {
            frappe.call({
                method: "fetch_service_item_subscription",
                doc: frm.doc,
                args: {
                    service: row.service,
                    pet: row.pet,
                },
                callback: function (r) {
                    const { price } = r.message;
                    if (!r.message) {
                        row.subscription = null;
                        row.subscription_package = null;
                        row.subscription_row = null;
                        row.service_item = null;
                        row.remaining_sessions = 0;
                        row.price = price;
                        frm.refresh_field("custom_appointment_services");
                        return;
                    }

                    const {
                        name,
                        row_name,
                        pet_service_package,
                        service_item,
                        remaining_sessions,
                    } = r.message;
                    row.subscription = name;
                    row.subscription_package = pet_service_package;
                    row.subscription_row = row_name;
                    row.price = price;
                    row.remaining_sessions = remaining_sessions;
                    row.service_item = service_item;
                    frm.refresh_field("custom_appointment_services");
                },
                freeze: true,
            });
        } else {
            row.subscription = null;
            row.subscription_package = null;
            row.subscription_row = null;
            row.service_item = null;
            row.remaining_sessions = 0;
            row.price = 0;
            frm.refresh_field("custom_appointment_services");
        }
    },
});

frappe.ui.form.on("Pet Appointment Addon", {
    custom_appointment_addons_remove(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    service_addon(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    rate(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
});
