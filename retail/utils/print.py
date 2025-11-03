import base64
import io
import json
import re
from typing import Optional

import frappe
from frappe.utils import fmt_money, flt, cint
from frappe.utils.pdf import get_pdf

try:
    from barcode import Code128, EAN13
    from barcode.writer import ImageWriter

    HAS_PYBARCODE = True
except Exception:
    HAS_PYBARCODE = False

try:
    import pyqrcode

    HAS_PYQRCODE = True
except Exception:
    HAS_PYQRCODE = False

def _ean13_value(val: str) -> Optional[str]:
    digits = re.sub(r"\D", "", val or "")
    if len(digits) == 12:
        s = sum(int(d) for d in digits[-1::-2])
        t = sum(int(d) for d in digits[-2::-2]) * 3
        cd = (10 - (s + t) % 10) % 10
        return digits + str(cd)
    if len(digits) == 13:
        return digits
    return None


def _trim_name(name: str, max_chars: int = 90) -> str:
    s = (name or "").strip()
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars].rsplit(" ", 1)[0]
    return (cut or s[:max_chars]).rstrip() + "…"


def _barcode_png_code128(value: str, dpi: int = 300) -> bytes:
    if not HAS_PYBARCODE:
        frappe.throw(
            "Missing dependency: python-barcode. Install `python-barcode` (Pillow required)."
        )
    buf = io.BytesIO()
    Code128(str(value or ""), writer=ImageWriter()).write(
        buf,
        {"dpi": int(dpi) or 300, "quiet_zone": 1, "write_text": False, "font_size": 0},
    )
    return buf.getvalue()


def _barcode_png_ean13(value: str, dpi: int = 300) -> bytes:
    if not HAS_PYBARCODE:
        frappe.throw(
            "Missing dependency: python-barcode. Install `python-barcode` (Pillow required)."
        )
    v = _ean13_value(str(value or ""))
    if not v:
        frappe.throw("Invalid EAN-13 value (must have 12 or 13 digits).")
    buf = io.BytesIO()
    EAN13(v, writer=ImageWriter()).write(
        buf,
        {"dpi": int(dpi) or 300, "quiet_zone": 1, "write_text": False, "font_size": 0},
    )
    return buf.getvalue()


def _normalize_svg(svg: str) -> str:
    """Make an SVG fill its container: remove width/height and add preserveAspectRatio."""
    if not svg:
        return svg
    svg = re.sub(r'\swidth="[^"]+"', "", svg)
    svg = re.sub(r'\sheight="[^"]+"', "", svg)
    if "preserveAspectRatio" not in svg:
        svg = svg.replace("<svg ", '<svg preserveAspectRatio="xMidYMid meet" ', 1)
    svg = svg.replace("<svg ", '<svg style="width:100%;height:100%;display:block;" ', 1)
    return svg


def _qrcode_svg(value: str) -> str:
    if not HAS_PYQRCODE:
        frappe.throw("Missing dependency: PyQRCode. Install `PyQRCode==1.2.1`.")
    qr = pyqrcode.create(
        str(value or ""), error="M", version=None, mode="binary", encoding="utf-8"
    )
    buf = io.BytesIO()
    qr.svg(buf, scale=4, quiet_zone=1, xmldecl=False)
    return _normalize_svg(buf.getvalue().decode("utf-8"))


def _qrcode_png(value: str) -> bytes:
    qr = pyqrcode.create(
        str(value or ""), error="M", version=None, mode="binary", encoding="utf-8"
    )
    buf = io.BytesIO()
    qr.png(buf, scale=4, quiet_zone=1)
    return buf.getvalue()


def _barcode_img_html(value: str, btype: str, bh: int) -> str:
    """Return HTML for barcode area confined to a fixed-height region."""
    kind = (btype or "Code128").strip()

    if kind == "QRCode":
        try:
            png = _qrcode_png(value)
            b64 = base64.b64encode(png).decode("ascii")
            return (
                f'<div style="height:{int(bh)}px; width:100%; overflow:hidden;">'
                f'<img src="data:image/png;base64,{b64}" alt="qrcode" '
                f'style="width:{int(bh)}px; height:{int(bh)}px; display:block; object-fit:contain;"></div>'
            )
        except Exception:
            svg = _qrcode_svg(value)
            return (
                f'<div style="height:{int(bh)}px; width:100%; overflow:hidden;">'
                f"{svg}</div>"
            )

    try:
        png = (
            _barcode_png_ean13(value)
            if kind == "EAN13"
            else _barcode_png_code128(value)
        )
    except Exception as ex:
        if HAS_PYBARCODE:
            png = _barcode_png_code128(value)
        else:
            frappe.throw(
                f"Barcode generation failed: {frappe.utils.escape_html(str(ex))}"
            )
    b64 = base64.b64encode(png).decode("ascii")
    return (
        f'<div style="height:{int(bh)}px; width:100%; overflow:hidden;">'
        f'<img src="data:image/png;base64,{b64}" alt="barcode" '
        f'style="width:100%; height:100%; display:block; object-fit:contain;"></div>'
    )


# ---------- main ----------
@frappe.whitelist()
def stickers(
    doctype: str,
    names: str,
    label_size: str = "60x25",
    copies: int = 1,
    price_source: str = "Price List Rate",
    barcode_type: str = "Barcode",
    barcode_source: str = "Item Code",
    barcode_height: int = 40,
    barcode_width: int = 3,
    gap_mm: float = 3.0,
    max_name_chars: int = 90,
    name_font_mm: float = 2.0,
    price_font_mm: float = 2.4,
):
    """wkhtmltopdf-friendly stickers: name → barcode → price; QR stays inside its cell."""
    copies_i = max(1, cint(copies))
    bh = max(24, cint(barcode_height))
    gap = max(0.0, min(flt(gap_mm) or 3.0, 20.0))
    name_font = max(1.6, flt(name_font_mm) or 2.0)
    price_font = max(1.8, flt(price_font_mm) or 2.4)
    max_name_chars = max(20, cint(max_name_chars) or 90)

    sizes = {
        "30x20": {"w": 30, "h": 20, "cols": 5},
        "38x25": {"w": 38, "h": 25, "cols": 4},
        "50x25": {"w": 50, "h": 25, "cols": 3},
        "60x25": {"w": 60, "h": 25, "cols": 3},
        "60x30": {"w": 60, "h": 30, "cols": 3},
    }
    if label_size not in sizes:
        label_size = "60x25"
    W = sizes[label_size]["w"]
    H = sizes[label_size]["h"]
    COLS = sizes[label_size]["cols"]

    if doctype != "Item":
        frappe.throw("Only Item is supported in this endpoint.")

    try:
        names_list = json.loads(names or "[]")
    except Exception:
        names_list = []
    if not names_list:
        frappe.throw("No items selected.")

    fields = [
        "name",
        "item_name",
        "item_code",
        "standard_rate",
        "valuation_rate",
        "last_purchase_rate",
        "stock_uom",
    ]
    items = frappe.get_all(
        "Item",
        filters={"name": ["in", names_list]},
        fields=fields,
        limit_page_length=10000,
    )

    first_barcode_map = {}
    if barcode_source == "First Item Barcode":
        rows = frappe.get_all(
            "Item Barcode",
            filters={"parent": ["in", [i["name"] for i in items]]},
            fields=["parent", "barcode"],
            order_by="creation asc",
            limit_page_length=100000,
        )
        for r in rows:
            if r.parent not in first_barcode_map and r.barcode:
                first_barcode_map[r.parent] = r.barcode

    price_list_rate_map = {}
    if price_source == "Price List Rate":
        default_pl = (
            frappe.db.get_single_value("Selling Settings", "selling_price_list") or None
        )
        if default_pl:
            ip_rows = frappe.get_all(
                "Item Price",
                filters={
                    "price_list": default_pl,
                    "item_code": ["in", [i["name"] for i in items]],
                },
                fields=["item_code", "price_list_rate", "currency"],
                limit_page_length=100000,
            )
            price_list_rate_map = {
                r.item_code: (r.price_list_rate, r.currency) for r in ip_rows
            }

    css = f"""
    <style>
      @media print {{
        @page {{ margin: 5mm; }}
        body {{ margin: 0; }}
      }}
      table.sheet {{
        border-collapse: separate;
        border-spacing: {gap}mm {gap}mm;
        width: 100%;
      }}
      table.sheet td.cell {{
        vertical-align: top;
        padding: 0;
        width: {W}mm;
        height: {H}mm;
      }}
      table.lbl {{
        width: {W}mm;
        height: {H}mm;
        border: 1px dashed #ddd;
        border-collapse: separate;
        table-layout: fixed;
        box-sizing: border-box;
        font-family: Inter, Arial, Helvetica, sans-serif;
        overflow: hidden;              /* ensure nothing leaks */
      }}
      table.lbl td {{ padding: 0 3mm; }}
      table.lbl tr:first-child td {{ padding-top: 2mm; }}
      table.lbl tr:last-child td {{ padding-bottom: 2mm; }}

      td.name-cell {{ vertical-align: top; }}
      td.barcode-cell {{
        vertical-align: middle;
        height: {bh}px;               /* hard reservation for barcode area */
        padding-top: 1mm;
        padding-bottom: 0.5mm;
        overflow: hidden;             /* clip any overflow */
      }}
      td.price-cell {{ vertical-align: bottom; }}

      .name {{
        font-weight: 600;
        font-size: {name_font}mm;
        line-height: 1.12;
        word-wrap: break-word;
      }}
      .price {{
        font-weight: 700;
        font-size: {price_font}mm;
        white-space: nowrap;
        text-align: right;
      }}
    </style>
    """

    cells_html = []
    for it in items:
        code = it.get("item_code") or it.get("name")
        raw_name = it.get("item_name") or code
        name = _trim_name(raw_name, max_name_chars)

        currency = it.get("default_currency") or frappe.defaults.get_global_default(
            "currency"
        )
        if price_source == "Price List Rate" and code in price_list_rate_map:
            price_val, cur2 = price_list_rate_map[code]
            currency = cur2 or currency
        else:
            key = price_source.lower().replace(" ", "_")
            price_val = it.get(key)
        price_txt = (
            fmt_money(price_val, currency=currency) if price_val is not None else ""
        )

        raw_value = (
            first_barcode_map.get(it["name"])
            if barcode_source == "First Item Barcode"
            else code
        )
        raw_value = raw_value or code
        if barcode_type == "Barcode":
            barcode_type = "EAN13"
        barcode_html = _barcode_img_html(raw_value, barcode_type, bh)

        label_inner = f"""
          <table class="lbl">
            <tr><td class="name-cell"><div class="name">{frappe.utils.escape_html(name)}</div></td></tr>
            <tr><td class="barcode-cell">{barcode_html}</td></tr>
            <tr><td class="price-cell"><div class="price">{frappe.utils.escape_html(price_txt)}</div></td></tr>
          </table>
        """

        for _ in range(copies_i):
            cells_html.append(f'<td class="cell">{label_inner}</td>')

    rows_html = []
    for i in range(0, len(cells_html), COLS):
        chunk = cells_html[i : i + COLS]
        if len(chunk) < COLS:
            chunk.extend(['<td class="cell"></td>'] * (COLS - len(chunk)))
        rows_html.append(f"<tr>{''.join(chunk)}</tr>")

    html = css + f"<table class='sheet'>{''.join(rows_html)}</table>"

    pdf_bytes = get_pdf(html)
    filename = f"Item-Stickers-{frappe.utils.nowdate()}.pdf"
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "download"
