from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)
    reorder_level = Column(Integer, default=10)
    supplier = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    invoice_items = relationship("InvoiceItem", back_populates="product")
    sales = relationship("Sale", back_populates="product")
