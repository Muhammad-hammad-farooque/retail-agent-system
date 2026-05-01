from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.customer import Customer
from ..models.user import User
from ..auth.jwt_handler import get_current_user

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
def get_all_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Customer).filter(Customer.is_active == True)
    if search:
        query = query.filter(Customer.name.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()


@router.get("/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{customer_id}/loyalty")
def update_loyalty(
    customer_id: int,
    points: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.loyalty_points += points
    db.commit()
    return {"customer_id": customer_id, "loyalty_points": customer.loyalty_points}
