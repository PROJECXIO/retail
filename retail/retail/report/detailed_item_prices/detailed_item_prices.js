// Copyright (c) 2025, Projecx Team and contributors
// For license information, please see license.txt

frappe.query_reports["Detailed Item Prices"] = {
	filters: [
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "price_list",
			label: __("Price List"),
			fieldtype: "Link",
			options: "Price List",
		},
		{
			fieldname: "items",
			label: __("Items Filter"),
			fieldtype: "Select",
			options: "Enabled Items only\nDisabled Items only\nAll Items",
			default: "Enabled Items only",
		},
		{
			fieldname: "include_services",
			label: __("Include Service Item"),
			fieldtype: "Check",
		},
	],
};
