import frappe
from frappe.utils import cint
from frappe.utils.nestedset import get_root_of

from erpnext.accounts.doctype.pos_invoice.pos_invoice import (
    get_bin_qty,
    get_pos_reserved_qty,
    get_bundle_availability,
)
from erpnext.selling.page.point_of_sale.point_of_sale import (
    search_by_term,
    filter_result_items,
    get_conditions,
    get_item_group_condition,
)


@frappe.whitelist()
def get_stock_availability(item_code, warehouse, pos_profile):
    if frappe.db.get_value("Item", item_code, "is_stock_item"):
        is_stock_item = True
        bin_qty = get_bin_qty(item_code, warehouse)
        pos_sales_qty = get_pos_reserved_qty(item_code, warehouse)
    
        if (
            frappe.db.get_single_value("Selling Settings", "rv_enable_dropshipping")
            and frappe.db.get_value(
                "POS Profile", pos_profile, "rv_enable_dropshipping"
            )
            and frappe.db.get_value("Item", item_code, "delivered_by_supplier")
        ):
            return bin_qty - pos_sales_qty, False

        return bin_qty - pos_sales_qty, is_stock_item
    else:
        is_stock_item = True
        if frappe.db.exists("Product Bundle", {"name": item_code, "disabled": 0}):
            return get_bundle_availability(item_code, warehouse), is_stock_item
        else:
            is_stock_item = False
            # Is a service item or non_stock item
            return 0, is_stock_item


@frappe.whitelist()
def get_items(start, page_length, price_list, item_group, pos_profile, search_term=""):
    warehouse, hide_unavailable_items = frappe.db.get_value(
        "POS Profile", pos_profile, ["warehouse", "hide_unavailable_items"]
    )

    result = []

    if search_term:
        result = search_by_term(search_term, warehouse, price_list) or []
        filter_result_items(result, pos_profile)
        if result:
            return result

    if not frappe.db.exists("Item Group", item_group):
        item_group = get_root_of("Item Group")

    condition = get_conditions(search_term)
    condition += get_item_group_condition(pos_profile)

    lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])

    bin_join_selection, bin_join_condition = "", ""
    if hide_unavailable_items:
        bin_join_selection = ", `tabBin` bin"
        bin_join_condition = "AND bin.warehouse = %(warehouse)s AND bin.item_code = item.name AND bin.actual_qty > 0"

    items_data = frappe.db.sql(
        """
		SELECT
			item.name AS item_code,
			item.item_name,
			item.description,
			item.stock_uom,
			item.image AS item_image,
			item.is_stock_item
		FROM
			`tabItem` item {bin_join_selection}
		WHERE
			item.disabled = 0
			AND item.has_variants = 0
			AND item.is_sales_item = 1
			AND item.is_fixed_asset = 0
			AND item.item_group in (SELECT name FROM `tabItem Group` WHERE lft >= {lft} AND rgt <= {rgt})
			AND {condition}
			{bin_join_condition}
		ORDER BY
			item.name asc
		LIMIT
			{page_length} offset {start}""".format(
            start=cint(start),
            page_length=cint(page_length),
            lft=cint(lft),
            rgt=cint(rgt),
            condition=condition,
            bin_join_selection=bin_join_selection,
            bin_join_condition=bin_join_condition,
        ),
        {"warehouse": warehouse},
        as_dict=1,
    )

    # return (empty) list if there are no results
    if not items_data:
        return result

    current_date = frappe.utils.today()

    for item in items_data:
        uoms = frappe.get_doc("Item", item.item_code).get("uoms", [])

        item.actual_qty, _ = get_stock_availability(
            item.item_code, warehouse, pos_profile
        )
        item.uom = item.stock_uom

        item_price = frappe.get_all(
            "Item Price",
            fields=[
                "price_list_rate",
                "currency",
                "uom",
                "batch_no",
                "valid_from",
                "valid_upto",
            ],
            filters={
                "price_list": price_list,
                "item_code": item.item_code,
                "selling": True,
                "valid_from": ["<=", current_date],
                "valid_upto": ["in", [None, "", current_date]],
            },
            order_by="valid_from desc",
            limit=1,
        )

        if not item_price:
            result.append(item)

        for price in item_price:
            uom = next(filter(lambda x: x.uom == price.uom, uoms), {})

            if price.uom != item.stock_uom and uom and uom.conversion_factor:
                item.actual_qty = item.actual_qty // uom.conversion_factor

            result.append(
                {
                    **item,
                    "price_list_rate": price.get("price_list_rate"),
                    "currency": price.get("currency"),
                    "uom": price.uom or item.uom,
                    "batch_no": price.batch_no,
                }
            )
    return {"items": result}
