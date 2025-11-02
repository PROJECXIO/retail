# apps/retail/retail/utils/print.py

from __future__ import annotations

import io
import json
import re
from typing import Optional

import frappe
from frappe.utils import fmt_money
from frappe.utils.pdf import get_pdf

# ------------------------------------------------------------
# Optional dependencies (graceful fallbacks with clear errors)
# ------------------------------------------------------------
try:
    from barcode import Code128, EAN13  # type: ignore
    from barcode.writer import SVGWriter  # type: ignore
    HAS_PYBARCODE = True
except Exception:  # pragma: no cover
    HAS_PYBARCODE = False

try:
    import pyqrcode  # PyQRCode==1.2.1
    HAS_PYQRCODE = True
except Exception:  # pragma: no cover
    HAS_PYQRCODE = False


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _ean13_value(val: str) -> Optional[str]:
    """Return 13-digit EAN string (compute check digit if 12 digits)."""
    digits = re.sub(r"\D", "", val or "")
    if len(digits) == 12:
        s = sum(int(d) for d in digits[-1::-2])
        t = sum(int(d) for d in digits[-2::-2]) * 3
        cd = (10 - (s + t) % 10) % 10
        return digits + str(cd)
    if len(digits) == 13:
        return digits
    return None


def _barcode_svg_code128(value: str, module_width_px: int = 2, height_px: int = 40) -> str:
    """Inline SVG for Code128."""
    if not HAS_PYBARCODE:
        frappe.throw("Missing dependency: python-barcode. Install it and restart Bench.")
    # wkhtmltopdf ~96dpi → px to mm ≈ px / 3.78
    module_width_mm = max(0.1, float(module_width_px) / 3.78)
    opts = {
        "module_width": module_width_mm,
        "module_height": float(height_px),
        "font_size": 0,
        "quiet_zone": 1,
        "write_text": False,
    }
    buf = io.BytesIO()
    Code128(value, writer=SVGWriter()).write(buf, opts)
    return buf.getvalue().decode("utf-8")


def _barcode_svg_ean13(value: str, module_width_px: int = 2, height_px: int = 40) -> str:
    """Inline SVG for EAN13. Accepts 12 or 13 digits; computes check digit if needed."""
    if not HAS_PYBARCODE:
        frappe.throw("Missing dependency: python-barcode. Install it and restart Bench.")
    v = _ean13_value(value)
    if not v:
        frappe.throw("Invalid EAN-13 value (must have 12 or 13 digits).")
    module_width_mm = max(0.1, float(module_width_px) / 3.78)
    opts = {
        "module_width": module_width_mm,
        "module_height": float(height_px),
        "font_size": 0,
        "quiet_zone": 1,
        "write_text": False,
    }
    buf = io.BytesIO()
    EAN13(v, writer=SVGWriter()).write(buf, opts)
    return buf.getvalue().decode("utf-8")


def _qrcode_svg_pyqrcode(value: str, height_px: int = 40) -> str:
    """
    Return inline SVG for QR code using PyQRCode (no Pillow).
    We let PyQRCode render SVG; scale heuristically toward height_px.
    """
    if not HAS_PYQRCODE:
        frappe.throw("Missing dependency: PyQRCode. Install PyQRCode==1.2.1 and restart Bench.")
    qr = pyqrcode.create(value, error="M", version=None, mode="alphanumeric", encoding="utf-8")
    # Scale: small height → scale 3, otherwise 5 (wkhtmltopdf will fit via CSS container)
    scale = 3 if int(height_px) <= 40 else 5
    buf = io.BytesIO()
    qr.svg(buf, scale=scale, quiet_zone=1, xmldecl=False)
    return buf.getvalue().decode("utf-8")


# ------------------------------------------------------------
# Main endpoint
# ------------------------------------------------------------
@frappe.whitelist()
def stickers(
    doctype: str,
    names: str,
    label_size: str = "size-60x25",       # default to a wider sticker
    copies: int = 1,
    price_source: str = "standard_rate",
    barcode_type: str = "Code128",        # "Code128" | "EAN13" | "QRCode"
    barcode_source: str = "item_code",    # "item_code" | "first_item_barcode"
    barcode_height: int = 40,
    barcode_width: int = 3,               # a bit thicker by default for wider labels
):
    """
    Generate a single PDF of stickers for the selected Items.

    - No File records created; PDF is streamed directly.
    - Barcodes inline: SVG (Code128/EAN13/QR), so no external HTTP fetches.
    - Wider sizes & dynamic columns per size.
    """

    # ---- normalize incoming types (HTTP query params arrive as strings) ----
    def _to_int(val, default):
        try:
            n = int(val)
            return n if n > 0 else default
        except Exception:
            return default

    copies_i = _to_int(copies, 1)
    bw = _to_int(barcode_width, 3)     # narrow bar width hint (1D)
    bh = _to_int(barcode_height, 40)   # target barcode height

    # map size -> number of columns per row (A4-ish; tweak for your sheet)
    size_columns = {
        "size-30x20": 5,
        "size-38x25": 4,
        "size-50x25": 3,
        "size-60x25": 3,   # wider
        "size-60x30": 3,   # wider + taller
    }

    # whitelist label sizes
    if label_size not in set(size_columns.keys()):
        label_size = "size-60x25"
    cols = size_columns[label_size]

    if doctype != "Item":
        frappe.throw("Only Item is supported in this endpoint.")

    try:
        names_list = json.loads(names or "[]")
    except Exception:
        names_list = []
    if not names_list:
        frappe.throw("No items selected.")

    # Fetch base fields (include default_currency: used for fmt_money)
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

    # First barcode per item if requested
    first_barcode_map = {}
    if barcode_source == "first_item_barcode":
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

    # Optional: price list
    price_list_rate_map = {}
    if price_source == "price_list_rate":
        default_pl = frappe.db.get_single_value("Selling Settings", "selling_price_list") or None
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
            price_list_rate_map = {r.item_code: (r.price_list_rate, r.currency) for r in ip_rows}

    # Styles (wider sizes + dynamic grid columns)
    css = f"""
    <style>
      @media print {{
        @page {{ margin: 5mm; }}
        body {{ margin: 0; }}
      }}
      .grid {{
        display: grid;
        grid-gap: 2mm;
        grid-template-columns: repeat({cols}, max-content);  /* fewer columns -> wider stickers */
        align-items: start;
      }}
      .label {{
        font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        border: 1px dashed #ddd;
        padding: 2mm 3mm;                 /* a touch more breathing room on wider labels */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        page-break-inside: avoid;
        overflow: hidden;
      }}

      /* Sizes (Width x Height) */
      .size-30x20 {{ width: 30mm; height: 20mm; }}
      .size-38x25 {{ width: 38mm; height: 25mm; }}
      .size-50x25 {{ width: 50mm; height: 25mm; }}
      .size-60x25 {{ width: 60mm; height: 25mm; }}  /* wider */
      .size-60x30 {{ width: 60mm; height: 30mm; }}  /* wider + taller */

      .row {{ display: flex; align-items: center; justify-content: space-between; gap: 2mm; }}
      .name {{
        font-weight: 600;
        font-size: 3mm;
        line-height: 1.15;
        /* allow full wrapping (no trimming) */
        white-space: normal;          /* was nowrap */
        overflow: visible;            /* was hidden */
        text-overflow: clip;          /* was ellipsis */
        word-break: break-word;       /* break long words/codes */
        flex: 1 1 auto;               /* take remaining space */
        min-width: 0;                 /* allow flex item to shrink & wrap */
        }}
      .price {{ font-weight: 700; font-size: 3.2mm; white-space: nowrap; }}
      .barcode {{ display: block; margin-top: 0.8mm; }}
      .tiny {{ font-size: 2.4mm; line-height: 1; text-align: center; margin-top: 0.6mm; }}

      /* Make inline SVG barcodes fill height nicely */
      .barcode-svg {{ height: {bh}px; width: 100%; }}
      .barcode-svg svg {{ height: 100%; width: 100%; }}
    </style>
    """

    # Build labels
    labels_html = ['<div class="grid">']

    for it in items:
        code = it.get("item_code") or it.get("name")
        name = it.get("item_name") or code

        # price
        currency = it.get("default_currency") or frappe.defaults.get_global_default("currency")
        if price_source == "price_list_rate" and code in price_list_rate_map:
            price_val, currency_from_ip = price_list_rate_map[code]
            currency = currency_from_ip or currency
        else:
            price_val = it.get(price_source)
        price_txt = fmt_money(price_val, currency=currency) if price_val else ""

        # barcode value
        if barcode_source == "first_item_barcode":
            raw_value = first_barcode_map.get(it["name"]) or code
        else:
            raw_value = code

        # render barcode inline
        btype = (barcode_type or "Code128").strip()
        try:
            if btype == "EAN13":
                svg = _barcode_svg_ean13(raw_value, bw, bh)
                barcode_markup = f'<div class="barcode barcode-svg">{svg}</div>'
            elif btype == "QRCode":
                if not HAS_PYQRCODE:
                    frappe.throw("PyQRCode is not installed. Install PyQRCode==1.2.1 and restart Bench.")
                svg = _qrcode_svg_pyqrcode(raw_value, bh)
                barcode_markup = f'<div class="barcode barcode-svg">{svg}</div>'
            else:
                svg = _barcode_svg_code128(raw_value, bw, bh)
                barcode_markup = f'<div class="barcode barcode-svg">{svg}</div>'
        except Exception as ex:
            # Fallback to Code128 if chosen type fails (and python-barcode is available)
            if HAS_PYBARCODE:
                svg = _barcode_svg_code128(raw_value, bw, bh)
                barcode_markup = f'<div class="barcode barcode-svg">{svg}</div>'
            else:
                frappe.throw(f"Barcode generation failed: {frappe.utils.escape_html(str(ex))}")

        for _ in range(copies_i):
            labels_html.append(
                f"""
                <div class="label {label_size}">
                  <div class="row">
                    <div class="name">{frappe.utils.escape_html(name)}</div>
                    <div class="price">{frappe.utils.escape_html(price_txt)}</div>
                  </div>
                  {barcode_markup}
                  <div class="tiny">{frappe.utils.escape_html(raw_value)}</div>
                </div>
                """
            )

    labels_html.append("</div>")
    html = css + "".join(labels_html)

    # Generate and stream the PDF
    pdf_bytes = get_pdf(html)
    filename = f"Item-Stickers-{frappe.utils.nowdate()}.pdf"
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "download"
