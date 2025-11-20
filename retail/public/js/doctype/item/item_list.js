frappe.listview_settings["Item"] = {
    onload: function (listview) {
        // Use defaults, or override filterField/api if needed
        window.retailAwesomebarListViewSearch(listview, {
            filterField: "item_code",
            api: "retail.utils.awesomebar.find_closest_items",
            storageKeyPrefix: "retail_subseq_last_q_",
        });

        // Custom buttons or other onload logic can be added here if needed
        listview.page.add_inner_button(__("Print Stickers"), async () => {
            const checked = listview.get_checked_items().map((d) => d.name);
            if (!checked.length) {
                frappe.msgprint(__("Please select at least one Item."));
                return;
            }
            let dialog = new frappe.ui.Dialog({
                title: __("Sticker Options"),
                fields: [
                    {
                        fieldname: "label_size",
                        label: __("Label Size"),
                        fieldtype: "Select",
                        options: ["30x20", "38x25", "50x25", "60x25", "60x30"],
                        default: "50x25",
                        reqd: 1,
                    },
                    {
                        fieldname: "copies",
                        label: __("Copies per Item"),
                        fieldtype: "Int",
                        default: 1,
                        reqd: 1,
                    },
                    {
                        fieldname: "price_source",
                        label: __("Price Source"),
                        fieldtype: "Select",
                        options: [
                            { label: __("Standard Rate"), value: "Standard Rate" },
                            { label: __("Valuation Rate"), value: "Valuation Rate" },
                            { label: __("Last Purchase Rate"), value: "Last Purchase Rate" },
                            { label: __("Price List Rate"), value: "Price List Rate" },
                        ],
                        default: "Price List Rate",
                        reqd: 1,
                    },
                    {
                        fieldname: "barcode_type",
                        label: __("Barcode Type"),
                        fieldtype: "Select",
                        options: ["Barcode", "QRCode"],
                        default: "Barcode",
                        reqd: 1,
                    },
                    {
                        fieldname: "barcode_source",
                        label: __("Barcode Value From"),
                        fieldtype: "Select",
                        options: [
                            { label: __("Item Code"), value: "Item Code" },
                            { label: __("First Item Barcode"), value: "First Item Barcode" },
                        ],
                        default: "Item Code",
                        reqd: 1,
                    },
                    {
                        fieldname: "barcode_height",
                        label: __("Barcode Height (px)"),
                        fieldtype: "Int",
                        default: 40,
                        reqd: 1,
                    },
                    {
                        fieldname: "barcode_width",
                        label: __("Narrow Bar Width (px)"),
                        fieldtype: "Int",
                        default: 2,
                        reqd: 1,
                    },
                ],
                primary_action(values) {
                    const qs = $.param({
                        doctype: "Item",
                        names: JSON.stringify(checked),
                        label_size: values.label_size,
                        copies: values.copies,
                        price_source: values.price_source,
                        barcode_type: values.barcode_type,
                        barcode_source: values.barcode_source,
                        barcode_height: values.barcode_height,
                        barcode_width: values.barcode_width,
                    });
                    const url = `/api/method/retail.utils.print.stickers?${qs}`;
                    dialog.hide();
                    window.open(url, "_blank");
                },
                primary_action_label: __("Print"),
            });
            dialog.show();
        });
    },
};
