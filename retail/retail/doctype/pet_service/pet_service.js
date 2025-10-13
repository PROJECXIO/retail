// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service", {
    update_total_price(frm) {
        let total_price = 0;
        let total_net_price = 0;
        (frm.doc.service_items || []).forEach(row => {
            total_price += flt(row.rate);
            if(row.discount_as == "Percent"){
                total_net_price += (flt(row.rate) - (flt(row.rate) * flt(row.discount) / 100));
            } else if(row.discount_as == "Fixed Amount"){
                total_net_price += (flt(row.rate) - flt(row.discount));
            } else {
                total_net_price += flt(row.rate);
            }
        });

        frm.set_value("total_price", total_price);
        frm.refresh_field("total_price");

        frm.set_value("total_net_price", total_net_price);
        frm.refresh_field("total_net_price");
    },
    validate(frm){
        (frm.doc.service_items || []).forEach(row => {
            if(row.item_code && row.discount_as == "Percent" && flt(row.discount) > 100){
                frappe.throw(__("Discount Percent at row {} can not be greater that 100", [row.idx]))
            }
            if(row.item_code && row.discount_as == "Fixed Amount" && flt(row.discount) >  flt(row.rate)){
                frappe.throw(__("Discount Amount at row {} can not be greater that rate {}", [row.idx, row.rate]))
            }
        });
    },
});

frappe.ui.form.on("Service Item", {
    service_items_remove(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    discount(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    discount_as(frm, cdt, cdn) {
        frm.trigger("update_total_price");
    },
    async item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            const value = await frappe.db.get_value(
                "Item Price",
                { item_code: row.item_code, uom: row.uom, selling: 1 },
                "price_list_rate"
            );
            const rate = (value && value.message && value.message.price_list_rate) || 0;
            row.rate = rate;
            frm.trigger("update_total_price");
        }else{
            row.rate = 0;
            frm.trigger("update_total_price");
        }
        
    },
});
