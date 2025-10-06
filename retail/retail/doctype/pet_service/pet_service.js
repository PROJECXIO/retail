// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service", {
    update_total_price(frm) {
        let total_price = (frm.doc.service_items || []).reduce(
            (prev, curr) => prev + flt(curr.rate),
            0
        );
        frm.set_value("total_price", total_price);
        frm.refresh_field("total_price");
    },
});

frappe.ui.form.on("Service Item", {
    service_items_remove(frm, cd, cn) {
        frm.trigger("update_total_price");
    },
    rate(frm, cd, cn) {
        frm.trigger("update_total_price");
    },
});
