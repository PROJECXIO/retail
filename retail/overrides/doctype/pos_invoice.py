import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.doctype.pos_invoice.pos_invoice import (
    POSInvoice as BasePOSInvoice,
)
from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order

from retail.overrides.whitelist.pos_invoice import get_stock_availability

class POSInvoice(BasePOSInvoice):
    def before_validate(self):
        for d in self.items:
            d.delivered_by_supplier = cint(frappe.db.get_value("Item", d.item_code, "delivered_by_supplier"))

    def validate_stock_availablility(self):
        if self.is_return:
            return

        if self.docstatus.is_draft() and not frappe.db.get_value(
            "POS Profile", self.pos_profile, "validate_stock_on_save"
        ):
            return

        from erpnext.stock.stock_ledger import is_negative_stock_allowed

        for d in self.get("items"):
            if not d.serial_and_batch_bundle:
                if is_negative_stock_allowed(item_code=d.item_code):
                    return
                available_stock, is_stock_item = get_stock_availability(
                    d.item_code, d.warehouse, self.pos_profile
                )

                item_code, warehouse, _qty = (
                    frappe.bold(d.item_code),
                    frappe.bold(d.warehouse),
                    frappe.bold(d.qty),
                )
                if is_stock_item and flt(available_stock) <= 0:
                    frappe.throw(
                        _(
                            "Row #{}: Item Code: {} is not available under warehouse {}."
                        ).format(d.idx, item_code, warehouse),
                        title=_("Item Unavailable"),
                    )
                elif is_stock_item and flt(available_stock) < flt(d.stock_qty):
                    frappe.throw(
                        _(
                            "Row #{}: Stock quantity not enough for Item Code: {} under warehouse {}. Available quantity {}."
                        ).format(d.idx, item_code, warehouse, available_stock),
                        title=_("Item Unavailable"),
                    )

    def before_submit(self):
        so = self.make_sales_order()
        if not so:
            return
        self.make_purchase_orders(so)
        
    
    def make_sales_order(self):
        profile_supplier = frappe.db.get_value("POS Profile", self.pos_profile, "rv_supplier")
        company_supplier = frappe.db.get_value("Dropshipping Default", {"company": self.company}, "supplier")
        so = frappe.new_doc("Sales Order")
        so.company = self.company
        so.customer = self.customer
        so.order_type = "Sales"
        so.transaction_date = self.posting_date
        so.delivery_date = self.due_date
        so.currency = self.currency
        so.selling_price_list = self.selling_price_list
        for item in self.items:
            if not item.delivered_by_supplier:
                continue
            item_supplier = frappe.db.get_value("Item Supplier", {"parenttype": "Item", "parent": item.item_code}, "supplier")
            supplier = profile_supplier or company_supplier or item_supplier
            if not supplier:
                continue
            so.append("items", {
                "item_code": item.item_code,
                "delivery_date": self.due_date,
                "qty": item.qty,
                "uom": item.uom,
                "delivered_by_supplier": item.delivered_by_supplier,
                "supplier": supplier,
            })
        if len(so.items) == 0:
            return None
        so.save(ignore_permissions=True)
        so.submit()
        return so

    def make_purchase_orders(self, so):
        by_supplier = {}

        for item in so.items:
            if item.delivered_by_supplier == 0:
                continue
            items_by_supp = by_supplier.get(item.supplier)
            if not items_by_supp:
                by_supplier.update({
                    f"{item.supplier}": [{
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "pending_qty": flt(item.stock_qty) - flt(item.ordered_qty),
                        "uom": item.uom,
                        "supplier": item.supplier,
                    }]
                })
            else:
                items_by_supp.append({
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "pending_qty": flt(item.stock_qty) - flt(item.ordered_qty),
                        "uom": item.uom,
                        "supplier": item.supplier,
                    })
        
        for k, v in by_supplier.items():
            po = make_purchase_order(source_name=so.name, selected_items=v)
            po.supplier = k
            po.save(ignore_permissions=True)
            po.submit()
            # po.update_status("Delivered")
