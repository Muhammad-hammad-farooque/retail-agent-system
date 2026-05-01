import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class ComplaintStatus(str, enum.Enum):
    received = "received"
    in_progress = "in_progress"
    resolved = "resolved"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    complaint = Column(Text, nullable=False)
    reference = Column(String(50), unique=True, nullable=False)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.received)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer")
