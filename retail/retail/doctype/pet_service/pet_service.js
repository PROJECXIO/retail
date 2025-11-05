// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service", {
    update_total_price(frm) {
        const price = (frm.doc.service_items || []).reduce((prev, curr) => prev + flt(curr.rate), 0);
        frm.set_value("total_price", price);
        frm.refresh_field("total_price");

        frm.set_value("selling_price", price);
        frm.refresh_field("selling_price");
    },
});

frappe.ui.form.on("Pet Service Item Detail", {
    service_items_remove(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    async pet_service_item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.pet_service_item) {
            frm.trigger("update_total_price");
        } else {
            row.rate = 0;
            frm.trigger("update_total_price");
        }
    },
    rate(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
});
