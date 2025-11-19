import frappe
from frappe.utils import flt

def execute():
    items = frappe.db.sql(
        """
            SELECT DISTINCT item_code
            FROM `tabItem`
            WHERE is_stock_item=1
        """,
        pluck="item_code",
    )
    ItemPrice = frappe.qb.DocType("Item Price")
    prices = (
        frappe.qb.from_(ItemPrice)
        .select(ItemPrice.name, ItemPrice.price_list_rate)
        .where(ItemPrice.item_code.isin(items))
        .run(as_dict=True)
    )
    for i in prices:
        price_list_rate = flt(i.price_list_rate)
        price_list_rate += price_list_rate * 0.05
        frappe.db.set_value("Item Price", i.name, "price_list_rate", price_list_rate)
    frappe.db.commit()


