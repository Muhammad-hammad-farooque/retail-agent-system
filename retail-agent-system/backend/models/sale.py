from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    revenue = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    sale_date = Column(DateTime(timezone=True), server_default=func.now())
    category = Column(String(100))

    product = relationship("Product", back_populates="sales")
