// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service", {
    async item(frm) {
        if(frm.doc.item){
            const value = await frappe.db.get_value(
                "Item Price",
                { item_code: frm.doc.item, uom: frm.doc.uom, selling: 1 },
                "price_list_rate"
            );
            const rate =
                (value && value.message && value.message.price_list_rate) || 0;
            frm.set_value("rate", rate);
            frm.refresh_field("rate");
            frm.trigger("update_total_price");
        }
	},
    discount(frm){
        frm.trigger("update_total_price");
    },
    discount_as(frm){
        frm.trigger("update_total_price");
    },
    update_total_price(frm) {
        let total_price = flt(frm.doc.rate);
        let total_net_price = 0;
        if(frm.doc.discount_as == "Percent"){
            total_net_price += (flt(frm.doc.rate) - (flt(frm.doc.rate) * flt(frm.doc.discount) / 100));
        } else if(frm.doc.discount_as == "Fixed Amount"){
            total_net_price += (flt(frm.doc.rate) - flt(frm.doc.discount));
        } else {
            total_net_price += flt(frm.doc.rate);
        }

        frm.set_value("total_price", total_price);
        frm.refresh_field("total_price");

        frm.set_value("total_net_price", total_net_price);
        frm.refresh_field("total_net_price");
    },
    validate(frm){
        if(frm.doc.item_code && frm.doc.discount_as == "Percent" && flt(frm.doc.discount) > 100){
            frappe.throw(__("Discount Percent can not be greater that 100"))
        }
        if(frm.doc.item_code && frm.doc.discount_as == "Fixed Amount" && flt(frm.doc.discount) >  flt(frm.doc.rate)){
            frappe.throw(__("Discount Amount can not be greater that rate {}", [frm.doc.rate]))
        }
    },
});
