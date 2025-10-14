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
        });

        if (frm.doc.discount_as == "Percent") {
            total_net_price +=
                flt(total_price) - (flt(total_price) * flt(frm.doc.discount)) / 100;
        } else if (frm.doc.discount_as == "Fixed Amount") {
            total_net_price += flt(total_price) - flt(frm.doc.discount);
        } else {
            total_net_price += flt(total_price);
        }

        frm.set_value("total_price", total_price);
        frm.refresh_field("total_price");

        frm.set_value("total_net_price", total_net_price);
        frm.refresh_field("total_net_price");
    },
    validate(frm) {
        if (
            frm.doc.item_code &&
            frm.doc.discount_as == "Percent" &&
            flt(frm.doc.discount) > 100
        ) {
            frappe.throw(__("Discount Percent can not be greater that 100"));
        }
        if (
            frm.doc.item_code &&
            frm.doc.discount_as == "Fixed Amount" &&
            flt(frm.doc.discount) > flt(frm.doc.rate)
        ) {
            frappe.throw(
                __("Discount Amount can not be greater that rate {}", [frm.doc.rate])
            );
        }
    },
});

frappe.ui.form.on("Pet Service Item", {
    service_items_remove(frm, cdt, cdn){
frm.trigger("update_total_price");
    },
    async item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item) {
            const value = await frappe.db.get_value(
                "Item Price",
                { item_code: row.item, uom: row.uom, selling: 1 },
                "price_list_rate"
            );
            const rate =
                (value && value.message && value.message.price_list_rate) || 0;
            row.rate = rate;
            frm.trigger("update_total_price");
        } else {
            row.rate = 0;
            frm.trigger("update_total_price");
        }
    },
});
