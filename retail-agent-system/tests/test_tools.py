"""Unit tests for all agent tools using SQLite in-memory DB."""
import pytest
from unittest.mock import patch, MagicMock

from tests.helpers import call_tool


class TestInventoryTools:

    def test_check_stock_found(self, sample_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import check_stock
            result = call_tool(check_stock, sample_product.id)

            assert "Test Samsung TV" in result
            assert "15" in result
            assert "OK" in result

    def test_check_stock_not_found(self, db):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import check_stock
            result = call_tool(check_stock, 9999)
            assert "not found" in result.lower()

    def test_low_stock_alert_shows_critical(self, low_stock_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [low_stock_product]
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import get_low_stock_alerts
            result = call_tool(get_low_stock_alerts)
            assert "LOW STOCK" in result

    def test_update_stock_negative_blocked(self, sample_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import update_stock
            result = call_tool(update_stock, sample_product.id, -999)
            assert "Cannot deduct" in result

    def test_create_purchase_order(self, sample_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            # Lookups in order: the product, an open PO today (none), the linked supplier (none)
            mock_db.query.return_value.filter.return_value.first.side_effect = [sample_product, None, None]
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import create_purchase_order
            result = call_tool(create_purchase_order, sample_product.id, 50)
            assert "Purchase Order" in result
            assert "PENDING APPROVAL" in result
            assert "Rs." in result


class TestAccountingTools:

    def test_financial_summary_returns_string(self):
        with patch("backend.tools.accounting_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
            mock_session.return_value = mock_db

            from backend.tools.accounting_tools import get_financial_summary
            result = call_tool(get_financial_summary)
            assert "Financial Summary" in result

    def test_profit_loss_returns_string(self):
        with patch("backend.tools.accounting_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_session.return_value = mock_db

            from backend.tools.accounting_tools import calculate_profit_loss
            result = call_tool(calculate_profit_loss, 30)
            assert "Profit & Loss" in result

    def test_revenue_by_category_no_data(self):
        with patch("backend.tools.accounting_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []
            mock_session.return_value = mock_db

            from backend.tools.accounting_tools import get_revenue_by_category
            result = call_tool(get_revenue_by_category)
            assert "No sales data" in result


class TestCustomerTools:

    def test_get_customer_info_masks_phone(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import get_customer_info
            result = call_tool(get_customer_info, sample_customer.id)
            assert "03001234567" not in result
            assert "4567" in result

    def test_get_customer_info_masks_address(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import get_customer_info
            result = call_tool(get_customer_info, sample_customer.id)
            assert "House 5, Street 3, Lahore" not in result

    def test_update_loyalty_points_success(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import update_loyalty_points
            result = call_tool(update_loyalty_points, sample_customer.id, 100)
            assert "Added" in result
            assert "100" in result

    def test_update_loyalty_points_insufficient(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import update_loyalty_points
            result = call_tool(update_loyalty_points, sample_customer.id, -99999)
            assert "Cannot deduct" in result

    def test_handle_complaint_returns_reference(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import handle_complaint
            result = call_tool(handle_complaint, sample_customer.id, "Product was damaged")
            assert "COMP-" in result
            assert "RECEIVED" in result


    @pytest.mark.parametrize("query", ["Test Cust", "0300-1234567", "+92 300 1234567", "923001234567"])
    def test_find_customer_by_name_or_phone(self, sample_customer, query):
        from tests.conftest import TestingSessionLocal
        with patch("backend.tools.customer_tools.SessionLocal", TestingSessionLocal):
            from backend.tools.customer_tools import find_customer
            result = call_tool(find_customer, query)
            assert f"ID {sample_customer.id}: Test Customer" in result
            assert "****4567" in result
            assert "03001234567" not in result

    def test_find_customer_by_id(self, sample_customer):
        from tests.conftest import TestingSessionLocal
        with patch("backend.tools.customer_tools.SessionLocal", TestingSessionLocal):
            from backend.tools.customer_tools import find_customer
            assert "Test Customer" in call_tool(find_customer, f"#{sample_customer.id}")

    def test_find_customer_no_match(self, sample_customer):
        from tests.conftest import TestingSessionLocal
        with patch("backend.tools.customer_tools.SessionLocal", TestingSessionLocal):
            from backend.tools.customer_tools import find_customer
            assert "No customers found" in call_tool(find_customer, "0311-9999999")


class TestMarketingTools:

    def test_update_price_below_cost_blocked(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import update_price
            result = call_tool(update_price, sample_product.id, 100.0)
            assert "below cost" in result.lower()
            assert "NOT updated" in result

    def test_update_price_success(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import update_price
            result = call_tool(update_price, sample_product.id, 90000.0)
            assert "Price updated" in result

    def test_create_promotion_excess_discount_blocked(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import create_promotion
            result = call_tool(create_promotion, sample_product.id, 95.0, "2026-05-01", "2026-05-31")
            assert "between 1% and 70%" in result

    def test_create_promotion_below_cost_blocked(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import create_promotion
            # price 85,000 / cost 65,000 -> max discount 23.5%
            result = call_tool(create_promotion, sample_product.id, 30.0, "2026-05-01", "2026-05-31")
            assert "below cost" in result.lower()
            assert "Maximum allowed" in result

    def test_create_promotion_valid(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import create_promotion
            result = call_tool(create_promotion, sample_product.id, 10.0, "2026-05-01", "2026-05-31")
            assert "Promotion Created" in result
            assert "ACTIVE" in result
