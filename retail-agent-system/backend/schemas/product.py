from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    sku: str
    category: str
    price: float
    cost_price: float
    quantity: int
    reorder_level: Optional[int] = 10
    supplier: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    quantity: Optional[int] = None
    reorder_level: Optional[int] = None
    supplier: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    price: float
    cost_price: float
    quantity: int
    reorder_level: int
    supplier: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
