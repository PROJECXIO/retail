# Copyright (c) 2025, Projecx Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
from frappe.utils import cint


def execute(filters=None):
    if not filters:
        filters = {}

    prices_list = get_prices_list(filters)
    columns = get_columns(prices_list)

    item_map = get_item_details(filters)
    barcode_map = get_item_barcodes(filters)
    pl = get_item_price_list(prices_list)

    data = []
    for item in sorted(item_map):
        barcodes = ", ".join([b.barcode for b in barcode_map.get(item, [])])
        row = {
            "item_code": item,
            "item_name": item_map[item]["item_name"],
            "item_group": item_map[item]["item_group"],
            "brand": item_map[item]["brand"],
            "description": item_map[item]["description"],
            "uom": item_map[item]["stock_uom"],
            "barcodes": barcodes,
        }
        for p in prices_list:
            price = pl.get(item, {}).get(p.name, {}).get("price")
            price_vat = pl.get(item, {}).get(p.name, {}).get("price_vat")
            row.update(
                {
                    f"{frappe.scrub(p.name)}": price,
                    f"{frappe.scrub(p.name)}_vat": price_vat,
                }
            )
        data.append(row)

    return columns, data


def get_columns(prices_list):
    """return columns based on filters"""
    columns = [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 120,
        },
        # {
        # 	"label": _("Description"),
        # 	"fieldname": "description",
        # 	"fieldtype": "Data",
        # 	"width": 120,
        # },
    ]
    for pl in prices_list:
        columns.append(
            {
                "label": _(pl.name),
                "fieldname": frappe.scrub(pl.name),
                "fieldtype": "Currency",
                "width": 150,
            },
        )
        columns.append(
            {
                "label": _(f"{pl.name} Inc VAT (5%)"),
                "fieldname": f"{frappe.scrub(pl.name)}_vat",
                "fieldtype": "Currency",
                "width": 170,
            },
        )
    columns.extend(
        [
            {
                "label": _("Item Group"),
                "fieldname": "item_group",
                "fieldtype": "Link",
                "options": "Item Group",
                "width": 120,
            },
            {
                "label": _("Brand"),
                "fieldname": "brand",
                "fieldtype": "Link",
                "options": "Brand",
                "width": 120,
            },
            {
                "label": _("Barcode"),
                "fieldname": "barcodes",
                "fieldtype": "Text",
                "width": 120,
            },
        ]
    )

    return columns


def get_item_details(filters):
    """returns all items details"""

    item_map = {}

    item = frappe.qb.DocType("Item")
    query = (
        frappe.qb.from_(item)
        .select(
            item.name,
            item.item_group,
            item.item_name,
            item.description,
            item.brand,
            item.stock_uom,
        )
        .orderby(item.item_code, item.item_group)
    )

    if filters.get("item_code"):
        query = query.where(item.item_code == filters.get("item_code"))
    if filters.get("item_group"):
        query = query.where(item.item_group == filters.get("item_group"))
    if cint(filters.get("include_services")) == 0:
        query = query.where(item.is_stock_item == 1)
    if filters.get("items") == "Enabled Items only":
        query = query.where(item.disabled == 0)
    elif filters.get("items") == "Disabled Items only":
        query = query.where(item.disabled == 1)

    for i in query.run(as_dict=True):
        item_map.setdefault(i.name, i)

    return item_map


def get_item_barcodes(filters):
    barocde_map = {}

    ItemBarcode = frappe.qb.DocType("Item Barcode")
    query = frappe.qb.from_(ItemBarcode).select(ItemBarcode.barcode, ItemBarcode.parent)

    if filters.get("item_code"):
        query = query.where(ItemBarcode.parent == filters.get("item_code"))

    for i in query.run(as_dict=True):
        barocde_map.setdefault(i.parent, []).append(i)

    return barocde_map


def get_item_price_list(prices_list):
    """Get selling & buying price list of every item"""

    rate = {}

    ip = frappe.qb.DocType("Item Price")
    pl = frappe.qb.DocType("Price List")
    cu = frappe.qb.DocType("Currency")
    prices_list = [r.name for r in prices_list]
    price_list = (
        frappe.qb.from_(ip)
        .from_(pl)
        .from_(cu)
        .select(
            ip.item_code,
            ip.buying,
            ip.selling,
            (IfNull(cu.symbol, ip.currency)).as_("currency"),
            ip.price_list_rate,
            ip.price_list,
        )
        .where(
            (ip.price_list == pl.name) & (pl.currency == cu.name) & (pl.enabled == 1)
        )
    )
    if len(prices_list) > 0:
        price_list = price_list.where(pl.name.isin(prices_list))
    price_list = price_list.run(as_dict=True)
    for d in price_list:
        price = round(d.price_list_rate, 2)
        price_vat = price + (price * 0.05)
        d.update({"price": f"{d.currency} {price}"})
        d.update({"price_vat": f"{d.currency} {price_vat}"})
        d.pop("currency")
        d.pop("price_list_rate")

        if d.price:
            rate.setdefault(d.item_code, {}).setdefault(
                d.price_list,
                {
                    "price": d.price,
                    "price_vat": d.price_vat,
                },
            )
    return rate


def get_prices_list(filters):
    PriceList = frappe.qb.DocType("Price List")
    query = (
        frappe.qb.from_(PriceList)
        .select(
            PriceList.name,
        )
        .where(PriceList.enabled == 1)
    )
    if filters.get("price_list"):
        query = query.where(PriceList.name == filters.get("price_list"))

    return query.run(as_dict=True)
