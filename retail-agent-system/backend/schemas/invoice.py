from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.models.invoice import InvoiceStatus


class InvoiceItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    customer_id: Optional[int]
    total_amount: float
    discount: float
    tax: float
    net_amount: float
    status: InvoiceStatus
    payment_method: Optional[str]
    created_at: datetime
    items: List[InvoiceItemOut] = []

    class Config:
        from_attributes = True


class InvoiceSummary(BaseModel):
    total_invoices: int
    total_revenue: float
    total_tax: float
    total_discount: float
    net_revenue: float
    paid_count: int
    pending_count: int
    cancelled_count: int
