// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Package Subscription", {
    additional_discount_as(frm){
        frm.trigger("update_total_price");
    },
    additional_discount(frm){
        frm.trigger("update_total_price");
    },
	update_total_price(frm) {
        let total_price = 0;
        let total_net_price = 0;
        (frm.doc.package_services || []).forEach(row => {
            total_price += flt(row.amount);
            let amount = 0;
            if (row.discount_as == "Percent") {
                amount = flt(row.amount) - (flt(row.amount) * flt(row.discount)) / 100;
            } else if (row.discount_as == "Fixed Amount") {
                amount = flt(row.amount) - flt(row.discount);
            } else {
                amount = flt(row.amount);
            }
            total_net_price += amount;
        });

        if (frm.doc.additional_discount_as == "Percent") {
            total_net_price =
                flt(total_net_price) - (flt(total_net_price) * flt(frm.doc.additional_discount)) / 100;
        } else if (frm.doc.additional_discount_as == "Fixed Amount") {
            total_net_price = flt(total_net_price) - flt(frm.doc.additional_discount);
        }

        frm.set_value("total_amount", total_price);
        frm.refresh_field("total_amount");

        frm.set_value("total_net_amount", total_net_price);
        frm.refresh_field("total_net_amount");
    },
    update_total_qty(frm){
        let total_qty = 0;
        let total_extra_qty = 0;
        (frm.doc.package_services || []).forEach(row => {
            total_qty += cint(row.qty);
            total_extra_qty += cint(row.extra_qty);
        });
        const total_net_qty = total_qty + total_extra_qty;
        frm.set_value("total_qty", total_qty);
        frm.refresh_field("total_qty");
        frm.set_value("total_extra_qty", total_extra_qty);
        frm.refresh_field("total_extra_qty");
        frm.set_value("total_net_qty", total_net_qty);
        frm.refresh_field("total_net_qty");
    },
});

frappe.ui.form.on("Package Service Subscription Details", {
    package_services_remove(frm, cd, cdn){
        frm.trigger("update_total_price");
        frm.trigger("update_total_qty");
    },
    pet_service_package(frm, cdt, cdn){
        frm.trigger("update_total_qty");
    },
    rate(frm, cdt, cdn){
        const row = locals[cdt][cdn];
        row.amount = flt(row.rate) * cint(row.qty);
        frm.trigger("update_total_price");
    },
    qty(frm, cdt, cdn){
        const row = locals[cdt][cdn];
        row.amount = flt(row.rate) * cint(row.qty);
        frm.trigger("update_total_price");
        frm.trigger("update_total_qty");
    },
    extra_qty(frm, cdt, cdn){
        frm.trigger("update_total_qty");
    },
    discount(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
    discount_as(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
})