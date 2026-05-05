from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/retaildb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    # Import all models so SQLAlchemy registers them before creating tables
    from .models import (  # noqa: F401
        Product, Invoice, InvoiceItem, Customer, Sale, User,
        Complaint, Supplier, PurchaseOrder, Promotion, Notification,
    )
    Base.metadata.create_all(bind=engine)
