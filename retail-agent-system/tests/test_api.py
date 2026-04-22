"""Integration tests for FastAPI endpoints."""
import pytest


class TestAuthEndpoints:

    def test_register_success(self, client):
        response = client.post("/auth/register", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123",
            "role": "staff",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "staff"
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client, admin_user):
        response = client.post("/auth/register", json={
            "username": "testadmin",
            "email": "another@example.com",
            "password": "pass123",
        })
        assert response.status_code == 400
        assert "taken" in response.json()["detail"].lower()

    def test_login_success(self, client, admin_user):
        response = client.post("/auth/login", data={
            "username": "testadmin",
            "password": "testpass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, admin_user):
        response = client.post("/auth/login", data={
            "username": "testadmin",
            "password": "wrongpass",
        })
        assert response.status_code == 401

    def test_me_endpoint(self, client, auth_headers):
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["username"] == "testadmin"

    def test_me_without_token(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestInventoryEndpoints:

    def test_get_products_requires_auth(self, client):
        response = client.get("/inventory/products")
        assert response.status_code == 401

    def test_get_products_success(self, client, auth_headers, sample_product):
        response = client.get("/inventory/products", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_critical_stock(self, client, auth_headers, low_stock_product):
        response = client.get("/inventory/critical", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        skus = [p["sku"] for p in data]
        assert "TEST-LOW-001" in skus

    def test_add_product_success(self, client, auth_headers):
        response = client.post("/inventory/products", headers=auth_headers, json={
            "name": "New Test Product",
            "sku": "NEW-TEST-999",
            "category": "Electronics",
            "price": 5000.0,
            "cost_price": 3000.0,
            "quantity": 20,
            "reorder_level": 5,
        })
        assert response.status_code == 201
        assert response.json()["sku"] == "NEW-TEST-999"

    def test_add_product_duplicate_sku(self, client, auth_headers, sample_product):
        response = client.post("/inventory/products", headers=auth_headers, json={
            "name": "Duplicate SKU",
            "sku": "TEST-001",
            "category": "Electronics",
            "price": 1000.0,
            "cost_price": 500.0,
            "quantity": 10,
        })
        assert response.status_code == 400

    def test_get_product_by_id(self, client, auth_headers, sample_product):
        response = client.get(f"/inventory/products/{sample_product.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Test Samsung TV"

    def test_get_product_not_found(self, client, auth_headers):
        response = client.get("/inventory/products/99999", headers=auth_headers)
        assert response.status_code == 404


class TestAccountingEndpoints:

    def test_get_invoices_requires_auth(self, client):
        response = client.get("/accounting/invoices")
        assert response.status_code == 401

    def test_get_invoices_success(self, client, auth_headers):
        response = client.get("/accounting/invoices", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_summary_success(self, client, auth_headers):
        response = client.get("/accounting/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_invoices" in data
        assert "net_revenue" in data
        assert "paid_count" in data

    def test_get_invoices_with_date_filter(self, client, auth_headers):
        response = client.get(
            "/accounting/invoices?start_date=2026-01-01&end_date=2026-12-31",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestDashboardEndpoints:

    def test_kpis_requires_auth(self, client):
        response = client.get("/dashboard/kpis")
        assert response.status_code == 401

    def test_kpis_success(self, client, auth_headers):
        response = client.get("/dashboard/kpis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_products" in data
        assert "low_stock_alerts" in data
        assert "monthly_revenue_pkr" in data
        assert "total_customers" in data

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
