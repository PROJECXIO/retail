frappe.provide("erpnext.PointOfSale");

frappe.pages["point-of-sale"].on_page_load = function (wrapper) {
    frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Point of Sale"),
        single_column: true,
    });

    frappe.require("point-of-sale.bundle.js", function () {
        const make_search_bar =
            erpnext.PointOfSale.ItemSelector.prototype.make_search_bar;
        erpnext.PointOfSale.ItemSelector.prototype.make_search_bar =
            function make_search_bar_with_barcode() {
                make_search_bar.call(this);
                const me = this;
                this.barcode_search_field = frappe.ui.form.make_control({
                    df: {
                        label: __("Search"),
                        fieldtype: "Data",
                        options: "Barcode",
                        onchange: function () {
                            me.set_search_value(this.value || "");
                            me.search_field.set_focus();
                        },
                    },
                    parent: this.$component.find(".item-group-field"),
                    render_input: true,
                });
                this.barcode_search_field.toggle_label(false);
            };

        erpnext.PointOfSale.Controller.prototype.get_available_stock = function (
            item_code,
            warehouse
        ) {
            const me = this;
            return frappe.call({
                method:
                    "erpnext.accounts.doctype.pos_invoice.pos_invoice.get_stock_availability",
                args: {
                    item_code: item_code,
                    warehouse: warehouse,
                    pos_profile: me.pos_profile,
                },
                callback(res) {
                    if (!me.item_stock_map[item_code]) me.item_stock_map[item_code] = {};
                    me.item_stock_map[item_code][warehouse] = res.message;
                },
            });
        };
        wrapper.pos = new erpnext.PointOfSale.Controller(wrapper);
        window.cur_pos = wrapper.pos;
    });
};
