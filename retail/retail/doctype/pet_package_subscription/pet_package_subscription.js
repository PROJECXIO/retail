// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Package Subscription", {
    refresh(frm) {
        frm.trigger("set_label");
        if (frm.doc.docstatus == 1 && !frm.doc.sales_invoice) {
            frm.add_custom_button(
                __("Prepare Invoice"),
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
                        title: __("Prepare Invoice"),
                        fields: [
                            {
                                fieldtype: "HTML",
                                fieldname: "info_message",
                                options: `
                                    <div style="padding:16px 0; color:#666;">
                                        ${__(
                                    "Prepare Invoice, this will create sales invoice?"
                                )}
                                    </div>
                                `,
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
                        ],
                        primary_action(data) {
                            frappe.call({
                                method: "create_invoice",
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
            );
        }
    },
    additional_discount_as(frm){
        frm.trigger("update_total_price");
    },
    additional_discount(frm){
        frm.trigger("update_total_price");
    },
	update_total_price(frm) {
        let total_price = 0;
        let total_net_price = 0;
        (frm.doc.package_services || []).forEach(row => {
            total_price += flt(row.amount);
            let amount = 0;
            if (row.discount_as == "Percent") {
                amount = flt(row.amount) - (flt(row.amount) * flt(row.discount)) / 100;
            } else if (row.discount_as == "Fixed Amount") {
                amount = flt(row.amount) - flt(row.discount);
            } else {
                amount = flt(row.amount);
            }
            total_net_price += amount;
        });

        if (frm.doc.additional_discount_as == "Percent") {
            total_net_price =
                flt(total_net_price) - (flt(total_net_price) * flt(frm.doc.additional_discount)) / 100;
        } else if (frm.doc.additional_discount_as == "Fixed Amount") {
            total_net_price = flt(total_net_price) - flt(frm.doc.additional_discount);
        }

        frm.set_value("total_amount", total_price);
        frm.refresh_field("total_amount");

        frm.set_value("total_net_amount", total_net_price);
        frm.refresh_field("total_net_amount");
    },
    update_total_qty(frm){
        let total_qty = 0;
        let total_extra_qty = 0;
        (frm.doc.package_services || []).forEach(row => {
            total_qty += cint(row.qty);
            total_extra_qty += cint(row.extra_qty);
        });
        const total_net_qty = total_qty + total_extra_qty;
        frm.set_value("total_qty", total_qty);
        frm.refresh_field("total_qty");
        frm.set_value("total_extra_qty", total_extra_qty);
        frm.refresh_field("total_extra_qty");
        frm.set_value("total_net_qty", total_net_qty);
        frm.refresh_field("total_net_qty");
    },
});

frappe.ui.form.on("Package Service Subscription Details", {
    package_services_remove(frm, cd, cdn){
        frm.trigger("update_total_price");
        frm.trigger("update_total_qty");
    },
    pet_service_package(frm, cdt, cdn){
        frm.trigger("update_total_qty");
    },
    rate(frm, cdt, cdn){
        const row = locals[cdt][cdn];
        row.amount = flt(row.rate) * cint(row.qty);
        frm.trigger("update_total_price");
    },
    qty(frm, cdt, cdn){
        const row = locals[cdt][cdn];
        row.amount = flt(row.rate) * cint(row.qty);
        frm.trigger("update_total_price");
        frm.trigger("update_total_qty");
    },
    extra_qty(frm, cdt, cdn){
        frm.trigger("update_total_qty");
    },
    discount(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
    discount_as(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
})