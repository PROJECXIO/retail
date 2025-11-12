// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service Package", {
    refresh(frm) {
        frm.set_query("service_item", "package_services", function (doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                query:
                    "retail.retail.doctype.pet_service_package.pet_service_package.service_item_query",
                filters: {
                    service: row.service,
                },
            };
        });
    },
    package_qty(frm) {
        frm.trigger("calculate_totals");
    },
    total_selling_price(frm) {
        frm.trigger("update_different_price");
    },
    update_different_price(frm) {
        frm.set_value(
            "different_price",
            flt(frm.doc.selling_price) - flt(frm.doc.total_selling_price)
        );
        frm.refresh_field("different_price");
    },
    calculate_totals(frm) {
        let total_services_rate = 0;
        let total_working_hours = 0;
        (frm.doc.package_services || []).forEach((row) => {
            total_services_rate += flt(row.selling_rate);
            total_working_hours += flt(row.working_hours);
        });

        frm.set_value("total_services_rate", total_services_rate);
        frm.set_value("total_services_amount", cint(frm.doc.package_qty) * total_services_rate);
        frm.set_value("total_working_hours", total_working_hours);
        frm.set_value("total_selling_amount", cint(frm.doc.package_qty) * total_services_rate);

        frm.refresh_fields([
            "total_services_rate",
            "total_services_amount",
            "total_working_hours",
            "total_selling_amount",
        ]);
    },
});

frappe.ui.form.on("Package Service", {
    package_services_remove(frm, cdt, cdn) {
        frm.trigger("calculate_totals");
    },
    service_item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.service_item) {
            row.qty = 0;
        } else {
            row.qty = 1;
        }
        frm.trigger("calculate_totals");
    },
    service(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.service) {
            row.service_item = null;
            row.qty = 0;
            row.working_hours = 0;
            row.rate = 0;
            row.selling_rate = 0;
        }
        frm.trigger("calculate_totals");
    },
    selling_rate(frm, cdt, cdn) {
        frm.trigger("calculate_totals");
    },
});
