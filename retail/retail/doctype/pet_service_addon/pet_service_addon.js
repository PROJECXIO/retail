// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service Addon", {
	async item(frm) {
        if(frm.doc.item){
            console.log(frm.doc.item)
            console.log(frm.doc.uom)
            const value = await frappe.db.get_value(
                "Item Price",
                { item_code: frm.doc.item, uom: frm.doc.uom, selling: 1 },
                "price_list_rate"
            );
            const rate =
                (value && value.message && value.message.price_list_rate) || 0;
            frm.set_value("rate", rate);
            frm.refresh_field("rate");
        }else{
            frm.set_value("rate", 0);
            frm.refresh_field("rate");
        }
	},
});
