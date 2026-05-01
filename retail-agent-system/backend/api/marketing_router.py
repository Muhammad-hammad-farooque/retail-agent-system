from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models.promotion import Promotion, PromotionStatus
from ..models.sale import Sale
from ..models.product import Product
from ..models.user import User
from ..auth.jwt_handler import get_current_user

router = APIRouter(prefix="/marketing", tags=["marketing"])


@router.get("/promotions")
def get_promotions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Promotion)
    if status:
        query = query.filter(Promotion.status == status)
    return query.order_by(Promotion.created_at.desc()).all()


@router.patch("/promotions/{promo_id}/status")
def update_promotion_status(
    promo_id: int,
    status: PromotionStatus,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    promo = db.query(Promotion).filter(Promotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    promo.status = status
    db.commit()
    return {"promo_id": promo_id, "status": promo.status}


@router.get("/trends")
def get_sales_trends(
    days: int = Query(30, ge=1, le=365),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(
        func.date(Sale.sale_date).label("date"),
        func.sum(Sale.revenue).label("revenue"),
        func.sum(Sale.quantity_sold).label("units"),
    ).filter(Sale.sale_date >= since)
    if category:
        query = query.filter(Sale.category == category)
    results = query.group_by(func.date(Sale.sale_date)).order_by(func.date(Sale.sale_date)).all()
    return [{"date": str(r.date), "revenue": r.revenue, "units": r.units} for r in results]


@router.get("/top-products")
def get_top_products(
    limit: int = Query(5, ge=1, le=20),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    results = (
        db.query(Sale.product_id, func.sum(Sale.revenue).label("revenue"), func.sum(Sale.quantity_sold).label("units"))
        .filter(Sale.sale_date >= since)
        .group_by(Sale.product_id)
        .order_by(func.sum(Sale.revenue).desc())
        .limit(limit)
        .all()
    )
    output = []
    for pid, revenue, units in results:
        product = db.query(Product).filter(Product.id == pid).first()
        output.append({
            "product_id": pid,
            "name": product.name if product else f"Product #{pid}",
            "category": product.category if product else "Unknown",
            "revenue": revenue,
            "units": units,
        })
    return output
