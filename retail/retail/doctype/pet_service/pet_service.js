// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service", {
    discount(frm) {
        frm.trigger("update_total_price");
    },
    discount_as(frm) {
        frm.trigger("update_total_price");
    },
    update_total_price(frm) {
        let total_price = 0;
        let total_net_price = 0;
        (frm.doc.service_items || []).forEach(row => {
            total_price += flt(row.rate);
            let amount = 0;
            if (row.discount_as == "Percent") {
                amount = flt(row.rate) - (flt(row.rate) * flt(row.discount)) / 100;
            } else if (row.discount_as == "Fixed Amount") {
                amount = flt(row.rate) - flt(row.discount);
            } else {
                amount = flt(row.rate);
            }
            total_net_price += amount;
        });

        frm.set_value("total_price", total_price);
        frm.refresh_field("total_price");

        frm.set_value("total_net_price", total_net_price);
        frm.refresh_field("total_net_price");
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
    discount_as(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    discount(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
});
