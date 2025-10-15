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
    },
    additional_discount_as(frm) {
        frm.trigger("update_total_price");
    },
    additional_discount(frm) {
        frm.trigger("update_total_price");
    },
    async update_total_price(frm) {
        let total_package_price = 0;
        let net_total_package_price = 0;
        (frm.doc.package_services || []).forEach((row) => {
            total_package_price += flt(row.rate);
            net_total_package_price += flt(row.rate);
        });

        if (frm.doc.additional_discount_as == "Percent") {
            net_total_package_price =
                net_total_package_price -
                (net_total_package_price * flt(frm.doc.additional_discount)) /
                100;
        } else if (frm.doc.additional_discount_as == "Fixed Amount") {
            net_total_package_price =
                net_total_package_price - flt(frm.doc.additional_discount);
        }

        await frm.set_value("total_package_price", total_package_price);
        await frm.refresh_field("total_package_price");

        await frm.set_value("net_total_package_price", net_total_package_price);
        await frm.refresh_field("net_total_package_price");
    },
    validate(frm) {
        (frm.doc.package_services || []).forEach((row) => {
            if (
                row.service &&
                row.discount_as == "Percent" &&
                flt(row.discount) > 100
            ) {
                frappe.throw(
                    __("Discount Percent at row {} can not be greater that 100", [
                        row.idx,
                    ])
                );
            }
            if (
                row.service &&
                row.discount_as == "Fixed Amount" &&
                flt(row.discount) > flt(row.rate)
            ) {
                frappe.throw(
                    __("Discount Amount at row {} can not be greater that rate {}", [
                        row.idx,
                        row.rate,
                    ])
                );
            }
        });
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
        if (row.service) {
            const value = await frappe.db.get_value(
                "Pet Service",
                row.service,
                "total_net_price"
            );
            const rate =
                (value && value.message && value.message.total_net_price) || 0;
            row.rate = rate;
            frm.trigger("update_total_price");
            frm.trigger("update_total_qty");
        } else {
            row.rate = 0;
            frm.trigger("update_total_price");
            frm.trigger("update_total_qty");
        }
    },
    qty(frm, cdt, cdn) {
        frm.trigger("update_total_qty");
    },
});
