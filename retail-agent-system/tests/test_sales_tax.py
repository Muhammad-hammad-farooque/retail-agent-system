"""Sales tax (SST) by payment method: 15% cash, 7% card and digital payments."""
from unittest.mock import patch

import pytest

from backend.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from backend.models.product import Product
from backend.models.sale import Sale
from backend.tax import format_rate, normalize_payment_method, sst_rate, tax_label
from tests.conftest import TestingSessionLocal
from tests.helpers import call_tool


@pytest.fixture(autouse=True)
def default_rates(monkeypatch):
    # Tests use the documented defaults unless they set a rate themselves
    monkeypatch.delenv("SST_RATE_CASH", raising=False)
    monkeypatch.delenv("SST_RATE_DIGITAL", raising=False)


def _sell(product_id, quantity, payment_method):
    from backend.tools.inventory_tools import sell_product
    with patch("backend.tools.inventory_tools.SessionLocal", TestingSessionLocal):
        return call_tool(sell_product, product_id, quantity, payment_method)


def _cleanup(db, invoice_numbers):
    for inv in db.query(Invoice).filter(Invoice.invoice_number.in_(invoice_numbers)).all():
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).delete()
        db.delete(inv)
    db.commit()


def _invoice_number(result):
    return next(line.split(":", 1)[1].strip() for line in result.splitlines() if line.startswith("Invoice"))


# ── Rates and payment methods ────────────────────────────────────────────────

@pytest.mark.parametrize("typed, method", [
    ("Cash", "Cash"), ("cash", "Cash"),
    ("Card", "Card"), ("credit card", "Card"), ("Debit Card", "Card"),
    ("JazzCash", "JazzCash"), ("jazz cash", "JazzCash"),
    ("EasyPaisa", "EasyPaisa"), ("easy paisa", "EasyPaisa"),
    ("Bank Transfer", "Bank Transfer"), ("bank", "Bank Transfer"),
    ("cheque", None), ("", None), (None, None),
])
def test_normalize_payment_method(typed, method):
    assert normalize_payment_method(typed) == method


@pytest.mark.parametrize("method, rate", [
    ("Cash", 0.15), ("Card", 0.07), ("JazzCash", 0.07), ("EasyPaisa", 0.07), ("Bank Transfer", 0.07),
])
def test_default_rates(method, rate):
    assert sst_rate(method) == rate


def test_rates_come_from_environment(monkeypatch):
    monkeypatch.setenv("SST_RATE_CASH", "0.18")
    monkeypatch.setenv("SST_RATE_DIGITAL", "0.05")
    assert sst_rate("Cash") == 0.18
    assert sst_rate("EasyPaisa") == 0.05


@pytest.mark.parametrize("value", ["15", "abc", "-0.1", "1.5"])
def test_invalid_rate_setting_is_rejected(monkeypatch, value):
    monkeypatch.setenv("SST_RATE_CASH", value)
    with pytest.raises(ValueError, match="SST_RATE_CASH"):
        sst_rate("Cash")


def test_labels():
    assert tax_label(0.15, "Cash") == "Tax (15% SST — Cash)"
    assert tax_label(0.07, "Card") == "Tax (7% SST — Card)"
    assert format_rate(0.075) == "7.5%"


# ── sell_product ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("typed, method, rate, label", [
    ("Cash", "Cash", 0.15, "Tax (15% SST — Cash)"),
    ("Card", "Card", 0.07, "Tax (7% SST — Card)"),
    ("jazz cash", "JazzCash", 0.07, "Tax (7% SST — JazzCash)"),
])
def test_sale_is_taxed_by_payment_method(db, sample_product, typed, method, rate, label):
    result = _sell(sample_product.id, 2, typed)
    number = _invoice_number(result)
    try:
        subtotal = 85000.0 * 2
        invoice = db.query(Invoice).filter(Invoice.invoice_number == number).one()
        assert invoice.payment_method == method
        assert invoice.total_amount == subtotal
        assert invoice.tax == round(subtotal * rate, 2)
        assert invoice.net_amount == round(subtotal * (1 + rate), 2)

        # The sale record holds revenue and profit before tax
        sale = db.query(Sale).filter(Sale.product_id == sample_product.id).order_by(Sale.id.desc()).first()
        assert sale.revenue == subtotal
        assert sale.profit == (85000.0 - 65000.0) * 2

        assert f"{label} : Rs.{subtotal * rate:,.0f}" in result
        assert f"Net Amount    : Rs.{subtotal * (1 + rate):,.0f}" in result
        assert "GST" not in result and "17%" not in result
    finally:
        db.query(Sale).filter(Sale.product_id == sample_product.id).delete()
        _cleanup(db, [number])


def test_sale_uses_rate_from_environment(db, sample_product, monkeypatch):
    monkeypatch.setenv("SST_RATE_CASH", "0.2")
    result = _sell(sample_product.id, 1, "Cash")
    number = _invoice_number(result)
    try:
        assert db.query(Invoice).filter(Invoice.invoice_number == number).one().tax == 17000.0
        assert "Tax (20% SST — Cash)" in result
    finally:
        db.query(Sale).filter(Sale.product_id == sample_product.id).delete()
        _cleanup(db, [number])


def test_unknown_payment_method_makes_no_sale(db, sample_product):
    invoices_before = db.query(Invoice).count()
    result = _sell(sample_product.id, 1, "cheque")
    assert "Unknown payment method 'cheque'" in result
    assert "No sale was made" in result
    db.refresh(sample_product)
    assert sample_product.quantity == 15
    assert db.query(Invoice).count() == invoices_before


def test_bad_rate_setting_makes_no_sale(db, sample_product, monkeypatch):
    monkeypatch.setenv("SST_RATE_DIGITAL", "seven")
    result = _sell(sample_product.id, 1, "Card")
    assert "Failed to process sale" in result and "SST_RATE_DIGITAL" in result
    db.refresh(sample_product)
    assert sample_product.quantity == 15


# ── Old invoices keep the tax they were charged ─────────────────────────────

@pytest.fixture
def old_invoice(db):
    """An invoice made before the SST change, taxed at the old 17%."""
    inv = Invoice(invoice_number="INV-OLD-17", total_amount=10000.0, discount=0.0, tax=1700.0,
                  net_amount=11700.0, status=InvoiceStatus.paid, payment_method="Card")
    db.add(inv)
    db.commit()
    yield inv
    _cleanup(db, ["INV-OLD-17"])


def test_new_sale_does_not_change_old_invoice(db, sample_product, old_invoice):
    number = _invoice_number(_sell(sample_product.id, 1, "Card"))
    try:
        db.refresh(old_invoice)
        assert (old_invoice.tax, old_invoice.net_amount) == (1700.0, 11700.0)
    finally:
        db.query(Sale).filter(Sale.product_id == sample_product.id).delete()
        _cleanup(db, [number])


def test_invoice_details_show_the_stored_rate(old_invoice):
    from backend.tools.accounting_tools import get_invoice
    with patch("backend.tools.accounting_tools.SessionLocal", TestingSessionLocal):
        result = call_tool(get_invoice, old_invoice.id)
    assert "Tax (17% — Card): Rs.1,700" in result


# ── Reports read the tax stored on each invoice ─────────────────────────────

def test_accounting_summary_sums_stored_tax(client, auth_headers, db):
    before = client.get("/accounting/summary", headers=auth_headers).json()
    db.add_all([
        Invoice(invoice_number="INV-SUM-CASH", total_amount=1000.0, discount=0.0, tax=150.0,
                net_amount=1150.0, status=InvoiceStatus.paid, payment_method="Cash"),
        Invoice(invoice_number="INV-SUM-CARD", total_amount=1000.0, discount=0.0, tax=70.0,
                net_amount=1070.0, status=InvoiceStatus.paid, payment_method="Card"),
    ])
    db.commit()
    try:
        after = client.get("/accounting/summary", headers=auth_headers).json()
        assert after["total_tax"] - before["total_tax"] == pytest.approx(220.0)
        assert after["net_revenue"] - before["net_revenue"] == pytest.approx(2220.0)
    finally:
        _cleanup(db, ["INV-SUM-CASH", "INV-SUM-CARD"])


def test_dashboard_transactions_show_stored_tax(client, auth_headers, db):
    db.add(Invoice(invoice_number="INV-DASH-EP", total_amount=2000.0, discount=0.0, tax=140.0,
                   net_amount=2140.0, status=InvoiceStatus.paid, payment_method="EasyPaisa"))
    db.commit()
    try:
        rows = client.get("/dashboard/recent-transactions?payment_method=EasyPaisa", headers=auth_headers).json()
        row = next(r for r in rows if r["invoice_number"] == "INV-DASH-EP")
        assert (row["tax"], row["net_amount"]) == (140.0, 2140.0)
    finally:
        _cleanup(db, ["INV-DASH-EP"])
