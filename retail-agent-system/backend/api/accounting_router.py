from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date

from ..database import get_db
from ..models.invoice import Invoice, InvoiceStatus
from ..models.user import User
from ..schemas.invoice import InvoiceOut, InvoiceSummary
from ..auth.jwt_handler import get_current_user

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("/invoices", response_model=List[InvoiceOut])
def get_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[InvoiceStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Invoice).options(joinedload(Invoice.items))
    if status:
        query = query.filter(Invoice.status == status)
    if start_date:
        query = query.filter(Invoice.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(Invoice.created_at <= datetime.combine(end_date, datetime.max.time()))
    return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/summary", response_model=InvoiceSummary)
def get_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Invoice)
    if start_date:
        query = query.filter(Invoice.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(Invoice.created_at <= datetime.combine(end_date, datetime.max.time()))

    all_invoices = query.all()
    paid = [i for i in all_invoices if i.status == InvoiceStatus.paid]

    return InvoiceSummary(
        total_invoices=len(all_invoices),
        total_revenue=sum(i.total_amount for i in all_invoices),
        total_tax=sum(i.tax for i in all_invoices),
        total_discount=sum(i.discount for i in all_invoices),
        net_revenue=sum(i.net_amount for i in paid),
        paid_count=len([i for i in all_invoices if i.status == InvoiceStatus.paid]),
        pending_count=len([i for i in all_invoices if i.status == InvoiceStatus.pending]),
        cancelled_count=len([i for i in all_invoices if i.status == InvoiceStatus.cancelled]),
    )
