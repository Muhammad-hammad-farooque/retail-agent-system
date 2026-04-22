"""Unit tests for all agent tools using SQLite in-memory DB."""
import pytest
from unittest.mock import patch, MagicMock


class TestInventoryTools:

    def test_check_stock_found(self, sample_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import check_stock
            result = check_stock(sample_product.id)

            assert "Test Samsung TV" in result
            assert "15" in result
            assert "OK" in result

    def test_check_stock_not_found(self, db):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import check_stock
            result = check_stock(9999)
            assert "not found" in result.lower()

    def test_low_stock_alert_shows_critical(self, low_stock_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [low_stock_product]
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import get_low_stock_alerts
            result = get_low_stock_alerts()
            assert "LOW STOCK" in result

    def test_update_stock_negative_blocked(self, sample_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import update_stock
            result = update_stock(sample_product.id, -999)
            assert "Cannot deduct" in result

    def test_create_purchase_order(self, sample_product):
        with patch("backend.tools.inventory_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.inventory_tools import create_purchase_order
            result = create_purchase_order(sample_product.id, 50)
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
            result = get_financial_summary()
            assert "Financial Summary" in result

    def test_profit_loss_returns_string(self):
        with patch("backend.tools.accounting_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_session.return_value = mock_db

            from backend.tools.accounting_tools import calculate_profit_loss
            result = calculate_profit_loss(30)
            assert "Profit & Loss" in result

    def test_revenue_by_category_no_data(self):
        with patch("backend.tools.accounting_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []
            mock_session.return_value = mock_db

            from backend.tools.accounting_tools import get_revenue_by_category
            result = get_revenue_by_category()
            assert "No sales data" in result


class TestCustomerTools:

    def test_get_customer_info_masks_phone(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import get_customer_info
            result = get_customer_info(sample_customer.id)
            assert "03001234567" not in result
            assert "4567" in result

    def test_get_customer_info_masks_address(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import get_customer_info
            result = get_customer_info(sample_customer.id)
            assert "House 5, Street 3, Lahore" not in result

    def test_update_loyalty_points_success(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import update_loyalty_points
            result = update_loyalty_points(sample_customer.id, 100)
            assert "Added" in result
            assert "100" in result

    def test_update_loyalty_points_insufficient(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import update_loyalty_points
            result = update_loyalty_points(sample_customer.id, -99999)
            assert "Cannot deduct" in result

    def test_handle_complaint_returns_reference(self, sample_customer):
        with patch("backend.tools.customer_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
            mock_session.return_value = mock_db

            from backend.tools.customer_tools import handle_complaint
            result = handle_complaint(sample_customer.id, "Product was damaged")
            assert "COMP-" in result
            assert "RECEIVED" in result


class TestMarketingTools:

    def test_update_price_below_cost_blocked(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import update_price
            result = update_price(sample_product.id, 100.0)
            assert "below cost" in result.lower()
            assert "NOT updated" in result

    def test_update_price_success(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import update_price
            result = update_price(sample_product.id, 90000.0)
            assert "Price updated" in result

    def test_create_promotion_excess_discount_blocked(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import create_promotion
            result = create_promotion(sample_product.id, 95.0, "2026-05-01", "2026-05-31")
            assert "below cost" in result.lower() or "Maximum allowed" in result

    def test_create_promotion_valid(self, sample_product):
        with patch("backend.tools.marketing_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_product
            mock_session.return_value = mock_db

            from backend.tools.marketing_tools import create_promotion
            result = create_promotion(sample_product.id, 10.0, "2026-05-01", "2026-05-31")
            assert "Promotion Created" in result
            assert "ACTIVE" in result
