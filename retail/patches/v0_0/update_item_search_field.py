import frappe

def execute():
    for i in frappe.db.sql("SELECT name, stock_uom, item_name, description, item_group, brand FROM `tabItem`"):
        search = []

        name = i[0]
        stock_uom = i[1]
        item_name = i[2]
        description = i[3]
        item_group = i[4]
        brand = i[5]

        if isinstance(name, str):
            search.append(name)
        if isinstance(stock_uom, str):
            search.append(stock_uom)
        if isinstance(item_name, str):
            search.append(item_name)
        if isinstance(description, str):
            search.append(description)
        if isinstance(item_group, str):
            search.append(item_group)
        if isinstance(brand, str):
            search.append(brand)
        search = "".join(search)
        frappe.db.set_value("Item", name, "custom_search",search)
    frappe.db.commit()
