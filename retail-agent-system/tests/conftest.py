import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.main import app
from backend.models.product import Product
from backend.models.customer import Customer
from backend.models.invoice import Invoice, InvoiceStatus
from backend.models.sale import Sale
from backend.models.user import User, UserRole
from backend.auth.jwt_handler import hash_password, create_token

# Use in-memory SQLite for tests — no PostgreSQL needed
TEST_DATABASE_URL = "sqlite:///./test_retail.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_product(db):
    product = Product(
        name="Test Samsung TV",
        sku="TEST-001",
        category="Electronics",
        price=85000.0,
        cost_price=65000.0,
        quantity=15,
        reorder_level=5,
        supplier="Samsung Pakistan",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    yield product
    db.delete(product)
    db.commit()


@pytest.fixture
def low_stock_product(db):
    product = Product(
        name="Low Stock Item",
        sku="TEST-LOW-001",
        category="Groceries",
        price=500.0,
        cost_price=300.0,
        quantity=3,
        reorder_level=10,
        supplier="Test Supplier",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    yield product
    db.delete(product)
    db.commit()


@pytest.fixture
def sample_customer(db):
    customer = Customer(
        name="Test Customer",
        email="testcustomer@example.com",
        phone="03001234567",
        address="House 5, Street 3, Lahore",
        loyalty_points=500,
        total_spent=50000.0,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    yield customer
    db.delete(customer)
    db.commit()


@pytest.fixture
def admin_user(db):
    user = User(
        username="testadmin",
        email="testadmin@example.com",
        hashed_password=hash_password("testpass123"),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture
def auth_headers(admin_user):
    token = create_token({"sub": admin_user.username, "role": admin_user.role})
    return {"Authorization": f"Bearer {token}"}
