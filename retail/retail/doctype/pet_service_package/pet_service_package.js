// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Service Package", {
    refresh(frm){
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
    update_total_totals(frm) {
        let total_package_price = 0;
        let selling_price = 0;
        let total_package_qty = 0;
        let total_working_hours = 0;
        (frm.doc.package_services || []).forEach((row) => {
            total_package_price += cint(row.qty) * flt(row.rate);
            selling_price += cint(row.qty) * flt(row.selling_rate);
            total_package_qty += cint(row.qty);
            total_working_hours += cint(row.qty) * flt(row.working_hours);
        });

        frm.set_value("total_package_price", total_package_price);
        frm.refresh_field("total_package_price");
        frm.set_value("selling_price", selling_price);
        frm.refresh_field("selling_price");
        frm.set_value("total_package_qty", total_package_qty);
        frm.refresh_field("total_package_qty");
        frm.set_value("total_working_hours", total_working_hours);
        frm.refresh_field("total_working_hours");

    },
});

frappe.ui.form.on("Package Service", {
    package_services_remove(frm, cdt, cdn) {
        frm.trigger("update_total_totals");
    },
    service_item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if(!row.service_item){
            row.qty = 0;
        }else{
            row.qty = 1;
        }
        frm.trigger("update_total_totals");
    },
    service(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.service_item = null;
        row.qty = 0;
        row.working_hours = 0;
        row.rate = 0;
        row.selling_rate = 0;
        frm.trigger("update_total_totals");
    },
    rate(frm, cdt, cdn){
        frm.trigger("update_total_totals");
    },
    qty(frm, cdt, cdn) {
        frm.trigger("update_total_totals");
    },
    selling_rate(frm, cdt, cdn) {
        frm.trigger("update_total_totals");
    },
});
