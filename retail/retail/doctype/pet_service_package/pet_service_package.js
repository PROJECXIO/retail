// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service Package", {
    async update_totals(frm) {
        let total_package_price = 0;
        let total_working_hours = 0;
        let total_package_qty = 0;

        (frm.doc.package_services || []).forEach((row) => {
            total_package_price += flt(row.amount);
            total_working_hours = total_working_hours + (flt(row.qty) * flt(row.working_hours))
            total_package_qty += row.qty ? cint(row.qty) : 1;
        });

        await frm.set_value("total_package_price", total_package_price);
        await frm.set_value("selling_price", total_package_price);
        await frm.refresh_field("total_package_price");
        await frm.refresh_field("selling_price");
        frm.set_value("total_working_hours", total_working_hours);
        frm.refresh_field("total_working_hours");
        frm.set_value("total_package_qty", total_package_qty);
        frm.refresh_field("total_package_qty");
    },
});

frappe.ui.form.on("Package Service", {
    package_services_remove(frm, cdt, cdn) {
        frm.trigger("update_totals");
    },
    rate(frm, cdt, cdn){
        const row = locals[cdt][cdn];
        row.amount = flt(row.rate) * cint(row.qty);
        frm.trigger("update_totals");
    },
    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.amount = flt(row.rate) * cint(row.qty);
        frm.trigger("update_totals");
    },

});
