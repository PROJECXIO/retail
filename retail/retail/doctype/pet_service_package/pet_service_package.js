// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service Package", {
    refresh(frm){
        frm.set_query("service", "package_services", function(doc){
            return {
                query: "retail.retail.doctype.pet_service_package.pet_service_package.service_query",
				filters: {
					pet_type: doc.pet_type,
					pet_size: doc.pet_size,
				},
            }
        });
        frm.set_query("service_item", "package_services", function(doc, cdt, cdn){
            const row = locals[cdt][cdn];
            return {
                query: "retail.retail.doctype.pet_service_package.pet_service_package.service_item_query",
				filters: {
					service: row.service,
				},
            }
        });
    },
    additional_discount_as(frm) {
        frm.trigger("update_total_price");
    },
    additional_discount(frm) {
        frm.trigger("update_total_price");
    },
    async update_total_price(frm) {
        let total_package_price = 0;
        (frm.doc.package_services || []).forEach((row) => {
            total_package_price += flt(row.rate);
        });

        await frm.set_value("total_package_price", total_package_price);
        await frm.refresh_field("total_package_price");

        await frm.set_value("net_total_package_price", net_total_package_price);
        await frm.refresh_field("net_total_package_price");
    },
    update_total_qty(frm) {
        let total_package_qty = 0;
        (frm.doc.package_services || []).forEach((row) => {
            total_package_qty += row.qty ? cint(row.qty) : 1;
        });

        frm.set_value("total_package_qty", total_package_qty);
        frm.refresh_field("total_package_qty");
    },
});

frappe.ui.form.on("Package Service", {
    package_services_remove(frm, cdt, cdn) {
        frm.trigger("update_total_price");
        frm.trigger("update_total_qty");
    },
    async service(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.service_item = null;
    },
    rate(frm, cdt, cdn){
        frm.trigger("update_total_price");
    },
    qty(frm, cdt, cdn) {
        frm.trigger("update_total_qty");
    },
});
