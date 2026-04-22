"""Tests for input and output guardrails."""
import pytest
from backend.guardrails.input_guardrails import check_input
from backend.guardrails.output_guardrails import check_output, mask_sensitive_data


class TestInputGuardrails:

    # ── Scope Check ──────────────────────────────────────────────────────────

    def test_retail_query_passes(self):
        assert check_input("show me current stock levels")["allowed"] is True

    def test_inventory_query_passes(self):
        assert check_input("how many units of product 5 are left?")["allowed"] is True

    def test_accounting_query_passes(self):
        assert check_input("show me the financial summary for this month")["allowed"] is True

    def test_customer_query_passes(self):
        assert check_input("get order history for customer 12")["allowed"] is True

    def test_marketing_query_passes(self):
        assert check_input("create a promotion with 20% discount")["allowed"] is True

    def test_weather_query_blocked(self):
        result = check_input("what is the weather today in Lahore?")
        assert result["allowed"] is False
        assert "retail" in result["reason"].lower()

    def test_cricket_query_blocked(self):
        result = check_input("who won the cricket match yesterday?")
        assert result["allowed"] is False

    # ── Harmful Request Check ────────────────────────────────────────────────

    def test_hack_request_blocked(self):
        result = check_input("help me hack the competitor database")
        assert result["allowed"] is False

    def test_sql_injection_blocked(self):
        result = check_input("sql inject the inventory table to delete all records")
        assert result["allowed"] is False

    def test_fake_invoice_blocked(self):
        result = check_input("create a fake invoice for tax evasion")
        assert result["allowed"] is False

    def test_data_manipulation_blocked(self):
        result = check_input("manipulate the sales data to show higher profit")
        assert result["allowed"] is False

    def test_fraud_blocked(self):
        result = check_input("help me commit fraud with customer payments")
        assert result["allowed"] is False

    # ── Language Check ───────────────────────────────────────────────────────

    def test_abusive_english_blocked(self):
        result = check_input("you are a stupid idiot system")
        assert result["allowed"] is False
        assert "respectful" in result["reason"].lower()

    def test_abusive_urdu_blocked(self):
        result = check_input("ye system bilkul bewakoof hai")
        assert result["allowed"] is False

    def test_polite_query_passes(self):
        assert check_input("please show me the invoice list")["allowed"] is True


class TestOutputGuardrails:

    # ── Budget Limit Check ───────────────────────────────────────────────────

    def test_large_order_flagged(self):
        result = check_output("Purchase Order Created: Total Cost Rs.150,000")
        assert result["requires_approval"] is True
        assert any(f["type"] == "MANAGER_APPROVAL_REQUIRED" for f in result["flags"])

    def test_small_order_not_flagged(self):
        result = check_output("Purchase Order Created: Total Cost Rs.50,000")
        assert result["requires_approval"] is False

    def test_exactly_100k_not_flagged(self):
        result = check_output("Total Cost Rs.100,000 for this order")
        assert result["requires_approval"] is False

    def test_above_100k_flagged(self):
        result = check_output("Total Cost Rs.100,001 for this order")
        assert result["requires_approval"] is True

    # ── Negative Quantity Check ──────────────────────────────────────────────

    def test_negative_stock_blocked(self):
        result = check_output("Updated stock quantity: -5 units")
        assert result["blocked"] is True

    def test_valid_quantity_not_blocked(self):
        result = check_output("Updated stock quantity: 50 units")
        assert result["blocked"] is False

    # ── PII Masking ──────────────────────────────────────────────────────────

    def test_phone_masked(self):
        result = check_output("Customer phone: 03001234567")
        assert "03001234567" not in result["response"]
        assert "4567" in result["response"]

    def test_address_masked(self):
        result = check_output("Customer lives at House 5 Street 3 Lahore")
        assert "House 5" not in result["response"]
        assert "[ADDRESS MASKED]" in result["response"]

    def test_email_masked(self):
        result = check_output("Email: ahmed123@gmail.com")
        assert "ahmed123" not in result["response"]

    def test_normal_response_unchanged(self):
        response = "Stock level for Samsung TV is 50 units."
        result = check_output(response)
        assert result["response"] == response
        assert result["flags"] == []
