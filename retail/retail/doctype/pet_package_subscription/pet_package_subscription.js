frappe.ui.form.on("Pet Package Subscription", {
    refresh(frm) {
        frm.trigger("set_label");
        frm.trigger("disable_items_table");
        // if (frm.doc.docstatus == 1 && !frm.doc.sales_invoice) {
            frm.trigger("add_invoice_button");
        // }
    },
    disable_items_table(frm) {
        const grid = frm.get_field("subscription_package_service").grid;
        grid.cannot_add_rows = true;
        grid.only_sortable = true;
        grid.cannot_delete_rows = true;
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
        });
    },
    validate(frm) {
        combine_package_service_duplicates(frm);
        frm.trigger("update_total_qty");
        frm.trigger("update_total_price");
    },

    package_services_remove(frm) {
        prune_details_by_alive_packages(frm);
        frm.trigger("update_total_qty");
        frm.trigger("update_total_price");
    },

    additional_discount_as(frm) {
        frm.trigger("update_total_price");
    },

    additional_discount(frm) {
        frm.trigger("update_total_price");
    },

    update_total_price(frm) {
        const pkgDisc = build_package_discount_map(frm);

        let total_price = 0.0;
        let total_net = 0.0;

        (frm.doc.subscription_package_service || []).forEach((r) => {
            const qty = flt(r.qty);
            const rate = flt(r.rate);
            const line_total = qty * rate;

            const pkg_percent = flt(pkgDisc[r.service_package] || 0);
            const item_percent = flt(r.discount || 0);

            const after_pkg = line_total * (1 - pkg_percent / 100.0);
            const net = after_pkg * (1 - item_percent / 100.0);

            r.amount = net;

            total_price += line_total;
            total_net += net;
        });

        if (frm.doc.additional_discount_as == "Percent") {
            total_net =
                flt(total_net) -
                (flt(total_net) * flt(frm.doc.additional_discount)) / 100;
        } else if (frm.doc.additional_discount_as == "Fixed Amount") {
            total_net = flt(total_net) - flt(frm.doc.additional_discount);
        }

        frm.refresh_field("subscription_package_service");

        frm.set_value("total_amount", total_price);
        frm.refresh_field("total_amount");
        frm.set_value("total_net_amount", total_net);
        frm.refresh_field("total_net_amount");
    },

    update_total_qty(frm) {
        let total_qty = 0;
        let total_extra_qty = 0;

        (frm.doc.package_services || []).forEach((row) => {
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
    package_services_remove(frm, cdt, cdn) {
        prune_details_by_alive_packages(frm);
        frm.trigger("update_total_qty");
        frm.trigger("update_total_price");
    },
    async pet_service_package(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row) return;

        if (!row.pet_service_package) {
            prune_details_by_alive_packages(frm);
            frm.trigger("update_total_qty");
            frm.trigger("update_total_price");
            return;
        }

        setTimeout(async () => {
            const dup = (frm.doc.package_services || []).find(
                (r) =>
                    r.name !== row.name &&
                    r.pet_service_package === row.pet_service_package
            );

            if (dup) {
                dup.qty = cint(dup.qty) + 1;
                const grid = frm.get_field("package_services").grid;
                const toRemove = grid.grid_rows_by_docname[row.name];
                if (toRemove) toRemove.remove();
                frm.refresh_field("package_services");
                sync_details_qty_from_service_row(frm, dup);
                frm.trigger("update_total_qty");
                frm.trigger("update_total_price");
                frappe.show_alert(
                    {
                        message: __(
                            `Increased qty to <b>${dup.qty}</b> for <b>${dup.pet_service_package}</b>`
                        ),
                        indicator: "green",
                    },
                    3
                );
                return;
            }

            const exists = await frappe.db.exists(
                "Pet Service Package",
                row.pet_service_package
            );
            if (!exists) {
                prune_details_by_alive_packages(frm);
                row.pet_service_package = "";
                row.qty = 0;
                frm.refresh_field("package_services");
                frm.trigger("update_total_qty");
                frm.trigger("update_total_price");
                frappe.show_alert(
                    {
                        message: __(
                            "Removed invalid package rows from Subscription Details"
                        ),
                        indicator: "orange",
                    },
                    3
                );
                return;
            }

            if (!cint(row.qty)) {
                row.qty = 1;
                frm.refresh_field("package_services");
            }

            const existsForRow = (frm.doc.subscription_package_service || []).some(
                (d) => d.source_package_row === row.name
            );
            if (existsForRow) {
                sync_details_qty_from_service_row(frm, row);
                frm.trigger("update_total_qty");
                frm.trigger("update_total_price");
                return;
            }

            const pkg = await frappe.db.get_doc(
                "Pet Service Package",
                row.pet_service_package
            );
            const multiplier = (cint(row.qty) || 0) + (cint(row.extra_qty) || 0) || 1;

            (pkg.package_services || []).forEach((ps) => {
                const d = frm.add_child("subscription_package_service");
                d.service_package = pkg.name;
                d.service = ps.service;
                d.service_item = ps.service_item;
                d.actual_qty = flt(ps.qty);
                d.qty = flt(ps.qty) * multiplier;
                d.rate = ps.rate;
                d.consumed_qty = 0;
                d.amount = flt(d.qty) * flt(d.rate);
                d.source_package_row = row.name;
            });

            frm.refresh_field("subscription_package_service");
            frm.trigger("update_total_qty");
            frm.trigger("update_total_price");
        }, 0);
    },

    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        sync_details_qty_from_service_row(frm, row);
        frm.trigger("update_total_qty");
        frm.trigger("update_total_price");
    },

    extra_qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        sync_details_qty_from_service_row(frm, row);
        frm.trigger("update_total_qty");
        frm.trigger("update_total_price");
    },
    discount(frm) {
        frm.trigger("update_total_price");
    },
});

frappe.ui.form.on("Subscription Package Service", {
    qty(frm, cdt, cdn) {
        recalc_detail_row_and_totals(frm, locals[cdt][cdn]);
    },
    rate(frm, cdt, cdn) {
        recalc_detail_row_and_totals(frm, locals[cdt][cdn]);
    },
    discount(frm, cdt, cdn) {
        recalc_detail_row_and_totals(frm, locals[cdt][cdn]);
    },
    subscription_package_service_remove(frm) {
        frm.trigger("update_total_price");
        frm.trigger("update_total_qty");
    },
});

function combine_package_service_duplicates(frm) {
    const rows = (frm.doc.package_services || []).slice();
    const byKey = new Map();
    const keep = [];

    rows.forEach((r) => {
        if (!r.pet_service_package) {
            keep.push(r);
            return;
        }
        const key = r.pet_service_package;
        if (byKey.has(key)) {
            const first = byKey.get(key);
            first.qty = cint(first.qty) + (cint(r.qty) || 1);
            first.extra_qty = cint(first.extra_qty) + cint(r.extra_qty);
        } else {
            byKey.set(key, r);
            keep.push(r);
            if (!cint(r.qty)) r.qty = 1;
            if (!cint(r.extra_qty)) r.extra_qty = 0;
        }
    });

    if (keep.length !== rows.length) {
        frm.doc.package_services = keep;
        frm.refresh_field("package_services");
    }
}

function sync_details_qty_from_service_row(frm, service_row) {
    if (!service_row) return;
    const multiplier =
        (cint(service_row.qty) || 0) + (cint(service_row.extra_qty) || 0);
    let changed = false;

    (frm.doc.subscription_package_service || []).forEach((d) => {
        if (
            d.source_package_row === service_row.name ||
            d.service_package === service_row.pet_service_package
        ) {
            const new_qty = flt(d.actual_qty) * multiplier;
            if (flt(d.qty) !== new_qty) {
                d.qty = new_qty;
                d.amount = flt(d.qty) * flt(d.rate);
                changed = true;
            }
        }
    });

    if (changed) {
        frm.refresh_field("subscription_package_service");
        frappe.show_alert(
            {
                message: __(
                    `Updated quantities for <b>${service_row.pet_service_package || "package"
                    }</b> (× ${multiplier})`
                ),
                indicator: "green",
            },
            3
        );
    }
}

function prune_details_by_alive_packages(frm) {
    const pkgRows = frm.doc.package_services || [];
    const aliveRowNames = new Set(pkgRows.map((r) => r.name));
    const alivePkgNames = new Set(
        pkgRows.map((r) => r.pet_service_package).filter(Boolean)
    );

    const before = (frm.doc.subscription_package_service || []).length;

    frm.doc.subscription_package_service = (
        frm.doc.subscription_package_service || []
    ).filter((d) => {
        if (d.source_package_row && !aliveRowNames.has(d.source_package_row))
            return false;
        if (d.service_package && !alivePkgNames.has(d.service_package))
            return false;
        return true;
    });

    if ((frm.doc.subscription_package_service || []).length !== before) {
        frm.refresh_field("subscription_package_service");
    }
}

function recalc_detail_row_and_totals(frm, d) {
    if (!d) return;
    const qty = flt(d.qty);
    const rate = flt(d.rate);
    const line_total = qty * rate;
    const discount_pct = flt(d.discount);
    const net = line_total - (line_total * discount_pct) / 100;

    d.amount = net;
    frm.refresh_field("subscription_package_service");

    frm.trigger("update_total_price");
}

function build_package_discount_map(frm) {
    const map = {};
    (frm.doc.package_services || []).forEach((row) => {
        if (row.pet_service_package) {
            map[row.pet_service_package] = flt(row.discount || 0);
        }
    });
    return map;
}
