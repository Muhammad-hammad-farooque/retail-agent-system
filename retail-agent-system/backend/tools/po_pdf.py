"""Purchase order PDF generation.

Renders a purchase order as a document a supplier can file or forward to
their accounts team. Uses fpdf2, the same library as the report scripts
under scripts/.
"""

from datetime import date, datetime

from fpdf import FPDF

# Palette — matches the dashboard's Aubergine & Ash brand colours.
ACCENT = (141, 72, 147)      # brand-600  #8d4893
DEEP = (95, 2, 100)          # brand-800  #5f0264
INK = (70, 12, 52)           # ash-900    #460c34
MUTED = (91, 79, 88)         # ash-600    #5b4f58
TINT = (235, 215, 239)       # brand-100  #ebd7ef
RULE = (222, 213, 224)       # ash-200    #ded5e0

COMPANY_NAME = "Retail Management System"
COMPANY_TAGLINE = "Intelligent Retail Store Automation"


def _safe(value) -> str:
    """fpdf2's core fonts are latin-1 only; drop anything they cannot encode.

    Product names and supplier addresses are free text, so a stray character
    would otherwise raise mid-render and lose the whole email.
    """
    text = "" if value is None else str(value)
    return text.encode("latin-1", "replace").decode("latin-1")


def _money(amount) -> str:
    """PKR, formatted without a symbol latin-1 cannot represent."""
    try:
        return f"Rs. {float(amount):,.0f}"
    except (TypeError, ValueError):
        return "Rs. 0"


class _PODocument(FPDF):
    def __init__(self, order_number: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.order_number = order_number
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(15, 15, 15)

    def header(self):
        # Brand bar
        self.set_fill_color(*DEEP)
        self.rect(0, 0, 210, 4, style="F")

        self.set_xy(15, 13)
        self.set_font("helvetica", "B", 17)
        self.set_text_color(*INK)
        self.cell(110, 8, "PURCHASE ORDER", new_x="LMARGIN", new_y="NEXT")

        self.set_x(15)
        self.set_font("helvetica", "", 9)
        self.set_text_color(*MUTED)
        self.cell(110, 5, _safe(COMPANY_NAME), new_x="LMARGIN", new_y="NEXT")
        self.set_x(15)
        self.cell(110, 5, _safe(COMPANY_TAGLINE), new_x="LMARGIN", new_y="NEXT")

        # PO number badge, right aligned
        self.set_xy(130, 13)
        self.set_font("helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(65, 5, "ORDER NUMBER", align="R", new_x="LEFT", new_y="NEXT")
        self.set_x(130)
        self.set_font("helvetica", "B", 13)
        self.set_text_color(*DEEP)
        self.cell(65, 7, _safe(self.order_number), align="R")

        self.set_y(38)
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        self.line(15, 38, 195, 38)
        self.set_y(44)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(*RULE)
        self.line(15, self.get_y(), 195, self.get_y())
        self.set_y(-12)
        self.set_font("helvetica", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(
            90,
            5,
            _safe(f"{COMPANY_NAME}  |  {self.order_number}"),
        )
        self.cell(90, 5, f"Page {self.page_no()} of {{nb}}", align="R")


def _label(pdf: FPDF, text: str) -> None:
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 4.5, _safe(text.upper()), new_x="LMARGIN", new_y="NEXT")


def _party_block(pdf: FPDF, x: float, y: float, width: float, title: str, lines) -> float:
    """One addressed party (vendor / ship-to). Returns the y it ended at."""
    pdf.set_xy(x, y)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(width, 4.5, _safe(title.upper()), new_x="LEFT", new_y="NEXT")

    first = True
    for line in lines:
        if not line:
            continue
        pdf.set_x(x)
        pdf.set_font("helvetica", "B" if first else "", 10 if first else 9)
        pdf.set_text_color(*(INK if first else MUTED))
        pdf.multi_cell(width, 4.8, _safe(line), new_x="LEFT", new_y="NEXT")
        first = False

    return pdf.get_y()


def build_po_pdf(supplier, po) -> bytes:
    """Render the purchase order. Returns raw PDF bytes."""
    pdf = _PODocument(order_number=str(po.order_number))
    pdf.alias_nb_pages()
    pdf.add_page()

    issued = po.created_at or datetime.now()
    issued_on = issued.strftime("%d %b %Y") if hasattr(issued, "strftime") else str(issued)
    status = getattr(po.status, "value", po.status) or "pending"

    # ── Parties ──────────────────────────────────────────────────────
    top = pdf.get_y()
    left_end = _party_block(
        pdf, 15, top, 85, "Vendor",
        [
            supplier.name,
            f"Attn: {supplier.contact_person}" if supplier.contact_person else None,
            supplier.address,
            supplier.phone,
            supplier.email,
        ],
    )
    right_end = _party_block(
        pdf, 110, top, 85, "Deliver to",
        [COMPANY_NAME, "Main Store Warehouse", "Receiving Department"],
    )
    pdf.set_y(max(left_end, right_end) + 5)

    # ── Order meta strip ─────────────────────────────────────────────
    pdf.set_fill_color(250, 248, 250)
    pdf.set_draw_color(*RULE)
    strip_y = pdf.get_y()
    pdf.rect(15, strip_y, 180, 13, style="DF")

    meta = [
        ("Issue date", issued_on),
        ("Status", str(status).replace("_", " ").title()),
        ("Currency", "PKR"),
    ]
    col = 180 / len(meta)
    for i, (key, val) in enumerate(meta):
        x = 15 + i * col
        pdf.set_xy(x + 4, strip_y + 2)
        pdf.set_font("helvetica", "", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(col - 8, 4, _safe(key.upper()), new_x="LEFT", new_y="NEXT")
        pdf.set_x(x + 4)
        pdf.set_font("helvetica", "B", 9.5)
        pdf.set_text_color(*INK)
        pdf.cell(col - 8, 5, _safe(val))
    pdf.set_y(strip_y + 13 + 7)

    # ── Line items ───────────────────────────────────────────────────
    _label(pdf, "Order details")
    pdf.ln(1)

    widths = [10, 74, 26, 18, 26, 26]
    headings = ["#", "Description", "SKU", "Qty", "Unit cost", "Amount"]
    aligns = ["C", "L", "L", "C", "R", "R"]

    pdf.set_fill_color(*TINT)
    pdf.set_draw_color(*RULE)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*DEEP)
    for w, head, align in zip(widths, headings, aligns):
        pdf.cell(w, 8, _safe(head), border=0, align=align, fill=True)
    pdf.ln()

    product = getattr(po, "product", None)
    name = getattr(product, "name", None) or "Item"
    sku = getattr(product, "sku", None) or "-"

    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*INK)
    row = [
        "1",
        _safe(name),
        _safe(sku),
        str(po.quantity),
        _money(po.unit_cost),
        _money(po.total_cost),
    ]
    y0 = pdf.get_y()
    for w, value, align in zip(widths, row, aligns):
        pdf.cell(w, 9, value, border=0, align=align)
    pdf.ln()
    pdf.set_draw_color(*RULE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    del y0

    # ── Totals ───────────────────────────────────────────────────────
    pdf.ln(3)
    for caption, value, strong in (
        ("Subtotal", _money(po.total_cost), False),
        ("Total (PKR)", _money(po.total_cost), True),
    ):
        pdf.set_x(118)
        if strong:
            pdf.set_fill_color(*TINT)
            pdf.set_font("helvetica", "B", 10.5)
            pdf.set_text_color(*DEEP)
            pdf.cell(41, 9, _safe(caption), align="R", fill=True)
            pdf.cell(36, 9, value, align="R", fill=True)
        else:
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(*MUTED)
            pdf.cell(41, 7, _safe(caption), align="R")
            pdf.set_text_color(*INK)
            pdf.cell(36, 7, value, align="R")
        pdf.ln()

    # ── Notes ────────────────────────────────────────────────────────
    if po.notes:
        pdf.ln(5)
        _label(pdf, "Notes")
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(*INK)
        pdf.set_x(15)
        # multi_cell leaves x at the right edge by default, so every
        # subsequent block must reset it or it renders into ~0mm of width.
        pdf.multi_cell(180, 4.8, _safe(po.notes), new_x="LMARGIN", new_y="NEXT")

    # ── Terms ────────────────────────────────────────────────────────
    pdf.ln(6)
    _label(pdf, "Terms")
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    for line in (
        "1.  Please confirm receipt of this order and provide an expected delivery date.",
        "2.  Quote the order number above on your delivery note and invoice.",
        "3.  Goods remain subject to inspection on arrival at the receiving department.",
        "4.  Quantities or prices differing from this order must be agreed in writing first.",
    ):
        pdf.set_x(15)
        pdf.multi_cell(180, 4.6, _safe(line), new_x="LMARGIN", new_y="NEXT")

    # ── Signatures ───────────────────────────────────────────────────
    pdf.ln(10)
    sign_y = pdf.get_y()
    pdf.set_draw_color(*RULE)
    for x, caption in ((15, "Authorised by  |  " + COMPANY_NAME), (110, "Accepted by  |  " + _safe(supplier.name))):
        pdf.line(x, sign_y, x + 85, sign_y)
        pdf.set_xy(x, sign_y + 1.5)
        pdf.set_font("helvetica", "", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(85, 4, _safe(caption))

    out = pdf.output()
    return bytes(out)


def po_pdf_filename(po) -> str:
    stamp = date.today().strftime("%Y%m%d")
    number = str(po.order_number).replace("/", "-").replace(" ", "")
    return f"PurchaseOrder-{number}-{stamp}.pdf"
