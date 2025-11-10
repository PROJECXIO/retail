frappe.ui.form.on("Pet Package Subscription", {
    refresh(frm) {
        frm.trigger("set_label");
        frm.trigger("disable_items_table");
        if (frm.doc.docstatus == 1 && !frm.doc.sales_invoice) {
            frm.trigger("add_invoice_button");
        }
    },

    disable_items_table(frm) {
        const grid = frm.get_field("subscription_package_service").grid;
        grid.cannot_add_rows = true;
        grid.only_sortable = true;
        grid.cannot_remove_rows = true;
        grid.refresh();
        grid.wrapper
            .find(".grid-add-row, .grid-add-multiple-rows, .grid-footer")
            .hide();
    },

    add_invoice_button(frm) {
        frm.add_custom_button(__("Prepare Invoice"), () => {
            const table_fields = [
                {
                    fieldname: "mode_of_payment",
                    fieldtype: "Link",
                    label: __("Mode of Payment"),
                    options: "Mode of Payment",
                    reqd: 1,
                },
                {
                    fieldname: "paid_amount",
                    fieldtype: "Currency",
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
                            </div>`,
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
                        data: [],
                        fields: table_fields,
                    },
                ],
                primary_action(data) {
                    frappe.call({
                        method: "create_invoice",
                        doc: frm.doc,
                        args: data,
                        callback: function () {
                            frm.reload_doc();
                        },
                    });
                    dialog.hide();
                },
                primary_action_label: __("Complete Appointment"),
            });

            dialog.show();
        });
    },

    selling_rate(frm) {
        frm.trigger("update_final_total");
    },
    subscription_qty(frm) {
        update_total_price(frm);
        frm.trigger("update_final_total");
    },
    additional_discount(frm) {
        frm.trigger("update_final_total");
    },
    update_final_total(frm) {
        const selling_amount =
            cint(frm.doc.subscription_qty || 0) * flt(frm.doc.selling_rate || 0);
        const net = selling_amount - (selling_amount * flt(frm.doc.additional_discount || 0)) / 100;
        frm.set_value("selling_amount", selling_amount);
        frm.set_value("total_net_selling_amount", net);

        frm.refresh_fields(["total_net_selling_amount", "selling_amount"]);
    },
});

frappe.ui.form.on("Package Service Subscription Details", {
    async pet_service_package(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row || !row.pet_service_package) return;

        const duplicate = (frm.doc.package_services || []).find(
            (r) =>
                r.name !== row.name && r.pet_service_package === row.pet_service_package
        );
        if (duplicate) {
            const grid = frm.get_field("package_services").grid;
            const toRemove = grid.grid_rows_by_docname[row.name];
            if (toRemove) toRemove.remove();

            frm.refresh_field("package_services");
            frappe.show_alert({
                message: __("Duplicate package removed — already added."),
                indicator: "orange",
            });
            return;
        }
        const exists = await frappe.db.exists(
            "Pet Service Package",
            row.pet_service_package
        );
        if (!exists) {
            row.pet_service_package = "";
            frm.refresh_field("package_services");
            frappe.show_alert({
                message: __("Invalid package removed."),
                indicator: "orange",
            });
            return;
        }
        update_total_price(frm);
    },

    package_services_remove(frm) {
        update_total_price(frm);
    },

    discount(frm) {
        update_total_price(frm);
    },

    selling_rate(frm) {
        update_total_price(frm);
    },
});

function compute_package_discount_factor(pkgRow) {
    const package_price = flt(pkgRow.package_price || 0);
    const selling = flt(pkgRow.selling_rate || 0);
    const rate_diff_discount =
        ((package_price - selling) / package_price) * 100.0;
    const pkg_discount = flt(pkgRow.discount || 0);
    return [rate_diff_discount, pkg_discount];
}

function build_package_discount_map(frm) {
    const map = {};
    (frm.doc.package_services || []).forEach((row) => {
        if (row.pet_service_package) {
            map[row.pet_service_package] = compute_package_discount_factor(row);
        }
    });
    return map;
}

function update_total_price(frm, update_selling_amount = true) {
    const pkg_discounts = build_package_discount_map(frm);
    let total_packages_amount = 0.0;
    let total_selling_amount = 0.0;
    let total_net_amount = 0.0;
    (frm.doc.package_services || []).forEach((r) => {
        total_packages_amount += flt(r.package_price);
        total_selling_amount += flt(r.selling_rate);
        let discounts = [0.0, 0.0];
        if (r.pet_service_package) {
            discounts = pkg_discounts[r.pet_service_package] || [0.0, 0.0];
        }
        let discount_value =
            flt(r.package_price) - (flt(r.package_price) * discounts[0]) / 100;
        discount_value =
            flt(discount_value) - (discounts[1] * flt(discount_value)) / 100;
        total_net_amount += discount_value;
    });
    const total_qty = cint(frm.doc.subscription_qty);
    frm.set_value("total_packages_amount", total_packages_amount);
    frm.set_value("total_selling_amount", total_selling_amount);
    frm.set_value("total_net_amount", total_net_amount);

    const fields = [
        "total_packages_amount",
        "total_selling_amount",
        "total_net_amount",
    ];
    if (update_selling_amount) {
        frm.set_value("selling_rate", total_net_amount);
        frm.set_value("selling_amount", total_qty * total_net_amount);
        fields.push("selling_rate");
        fields.push("selling_amount");
    }
    frm.refresh_fields(fields);
}
