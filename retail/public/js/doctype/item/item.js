frappe.ui.form.on("Item", {
    onload: function (frm) {
        frm.set_query(
            "custom_supplier_warehouse",
            "supplier_items",
            (doc, cdt, cdn) => {
                let row = locals[cdt][cdn];
                return {
                    filters: {
                        company: row.custom_warehouse_company,
                        is_group: 0,
                    },
                };
            }
        );
    },
});
