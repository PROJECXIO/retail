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
    selling_amount(frm) {
        frm.trigger("calculate_total_net_amount");
    },
    additional_discount(frm) {
        frm.trigger("calculate_total_net_amount");
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
    calculate_total_net_amount(frm) {
        frm.set_value(
            "total_net_selling_amount",
            flt(frm.doc.selling_amount) -
            (flt(frm.doc.additional_discount) * flt(frm.doc.selling_amount)) / 100
        );
    },
    calculate_totals(frm) {
        let total_packages_amount = 0;
        let total_selling_amount = 0;
        let total_net_amount = 0;
        let total_working_hours = 0;
        (frm.doc.package_services || []).forEach((row) => {
            total_packages_amount += flt(row.total_amount);
            total_selling_amount += flt(row.selling_amount);
            total_net_amount +=
                flt(row.selling_amount) -
                (flt(row.discount) * flt(row.selling_amount)) / 100;
            total_working_hours += flt(row.working_hours);
        });

        frm.set_value("total_packages_amount", total_packages_amount);
        frm.set_value("total_selling_amount", total_selling_amount);
        frm.set_value("total_net_amount", total_net_amount);
        frm.set_value("grand_total", total_net_amount);
        frm.set_value("outstanding_amount", total_net_amount);
        frm.set_value("selling_amount", total_net_amount);
        frm.set_value("total_working_hours", total_working_hours);

        frm.refresh_fields([
            "total_packages_amount",
            "total_selling_amount",
            "total_net_amount",
            "total_working_hours",
            "selling_amount",
        ]);
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
        frm.trigger("calculate_totals");
    },

    package_services_remove(frm) {
        frm.trigger("calculate_totals");
    },

    discount(frm) {
        frm.trigger("calculate_totals");
    },

    selling_rate(frm) {
        frm.trigger("calculate_totals");
    },
});
