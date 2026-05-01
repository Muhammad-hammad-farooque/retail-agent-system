import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class PromotionStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    discount_pct = Column(Float, nullable=False)
    original_price = Column(Float, nullable=False)
    promo_price = Column(Float, nullable=False)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    status = Column(Enum(PromotionStatus), default=PromotionStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product")
