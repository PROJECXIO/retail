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

        if (frm.doc.discount_as == "Percent") {
            total_net_price =
                flt(total_net_price) - (flt(total_net_price) * flt(frm.doc.discount)) / 100;
        } else if (frm.doc.discount_as == "Fixed Amount") {
            total_net_price = flt(total_net_price) - flt(frm.doc.discount);
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
    discount_as(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    discount(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
});
