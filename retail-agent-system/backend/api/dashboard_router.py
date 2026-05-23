from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta, timezone
from typing import Optional
import asyncio

from ..database import get_db
from ..models.product import Product
from ..models.invoice import Invoice, InvoiceStatus, InvoiceItem
from ..models.sale import Sale
from ..models.customer import Customer
from ..auth.jwt_handler import get_current_user
from ..models.user import User

router = APIRouter(tags=["dashboard"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active_connections.remove(ws)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.get("/dashboard/kpis")
def get_kpis(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0)
    week_start = today - timedelta(days=7)

    total_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()
    low_stock = db.query(func.count(Product.id)).filter(
        Product.is_active == True, Product.quantity <= Product.reorder_level
    ).scalar()

    monthly_revenue = db.query(func.sum(Invoice.net_amount)).filter(
        Invoice.status == InvoiceStatus.paid,
        Invoice.created_at >= month_start,
    ).scalar() or 0.0

    weekly_revenue = db.query(func.sum(Invoice.net_amount)).filter(
        Invoice.status == InvoiceStatus.paid,
        Invoice.created_at >= week_start,
    ).scalar() or 0.0

    total_customers = db.query(func.count(Customer.id)).scalar()
    total_invoices = db.query(func.count(Invoice.id)).scalar()

    top_categories = (
        db.query(Sale.category, func.sum(Sale.revenue).label("revenue"))
        .group_by(Sale.category)
        .order_by(func.sum(Sale.revenue).desc())
        .limit(5)
        .all()
    )

    return {
        "total_products": total_products,
        "low_stock_alerts": low_stock,
        "monthly_revenue_pkr": round(monthly_revenue, 2),
        "weekly_revenue_pkr": round(weekly_revenue, 2),
        "total_customers": total_customers,
        "total_invoices": total_invoices,
        "top_categories": [{"category": c, "revenue": round(r, 2)} for c, r in top_categories],
        "generated_at": today.isoformat(),
    }


@router.get("/dashboard/sales-today")
def get_sales_today(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc)
    day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)

    invoices = db.query(Invoice).filter(
        Invoice.status == InvoiceStatus.paid,
        Invoice.created_at >= day_start,
    ).all()

    return {
        "count": len(invoices),
        "revenue": round(sum(i.net_amount for i in invoices), 2),
    }


@router.get("/dashboard/daily-revenue")
def get_daily_revenue(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)

    results = (
        db.query(
            cast(Invoice.created_at, Date).label("day"),
            func.sum(Invoice.net_amount).label("revenue"),
            func.count(Invoice.id).label("count"),
        )
        .filter(Invoice.status == InvoiceStatus.paid, Invoice.created_at >= since)
        .group_by(cast(Invoice.created_at, Date))
        .order_by(cast(Invoice.created_at, Date))
        .all()
    )

    revenue_map = {str(r.day): {"revenue": round(r.revenue, 2), "count": r.count} for r in results}

    output = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        key = str(d)
        output.append({
            "date": key,
            "label": d.strftime("%b %d"),
            "revenue": revenue_map.get(key, {}).get("revenue", 0),
            "count": revenue_map.get(key, {}).get("count", 0),
        })

    return output


@router.get("/dashboard/recent-transactions")
def get_recent_transactions(
    payment_method: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Invoice).filter(Invoice.status == InvoiceStatus.paid)
    if payment_method:
        q = q.filter(Invoice.payment_method == payment_method)
    invoices = q.order_by(Invoice.created_at.desc()).limit(10).all()

    return [
        {
            "invoice_number": inv.invoice_number,
            "customer_id": inv.customer_id,
            "total_amount": round(inv.total_amount, 2),
            "tax": round(inv.tax, 2),
            "net_amount": round(inv.net_amount, 2),
            "payment_method": inv.payment_method,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invoices
    ]


@router.get("/dashboard/category-revenue")
def get_category_revenue(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    results = (
        db.query(Sale.category, func.sum(Sale.revenue).label("revenue"), func.sum(Sale.profit).label("profit"))
        .group_by(Sale.category)
        .order_by(func.sum(Sale.revenue).desc())
        .limit(8)
        .all()
    )
    return [
        {"category": r.category, "revenue": round(r.revenue, 2), "profit": round(r.profit, 2)}
        for r in results
    ]


@router.get("/dashboard/top-products")
def get_top_products(
    period: str = Query("week", pattern="^(today|week|month)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    if period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        since = now - timedelta(days=7)

    results = (
        db.query(
            Product.name,
            Product.category,
            func.sum(Sale.quantity_sold).label("units_sold"),
            func.sum(Sale.revenue).label("revenue"),
        )
        .join(Sale, Sale.product_id == Product.id)
        .filter(Sale.sale_date >= since)
        .group_by(Product.id, Product.name, Product.category)
        .order_by(func.sum(Sale.revenue).desc())
        .limit(8)
        .all()
    )

    return [
        {
            "name": r.name,
            "category": r.category,
            "units_sold": r.units_sold,
            "revenue": round(r.revenue, 2),
        }
        for r in results
    ]


@router.get("/dashboard/profit-summary")
def get_profit_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_profit = db.query(func.sum(Sale.profit)).filter(Sale.sale_date >= day_start).scalar() or 0.0

    today_invoices = db.query(Invoice).filter(
        Invoice.status == InvoiceStatus.paid,
        Invoice.created_at >= day_start,
    ).all()

    avg_order_value = 0.0
    if today_invoices:
        avg_order_value = sum(i.net_amount for i in today_invoices) / len(today_invoices)

    payment_breakdown = (
        db.query(Invoice.payment_method, func.count(Invoice.id).label("count"), func.sum(Invoice.net_amount).label("revenue"))
        .filter(Invoice.status == InvoiceStatus.paid)
        .group_by(Invoice.payment_method)
        .all()
    )

    return {
        "today_profit": round(today_profit, 2),
        "avg_order_value": round(avg_order_value, 2),
        "payment_breakdown": [
            {"method": r.payment_method or "Cash", "count": r.count, "revenue": round(r.revenue, 2)}
            for r in payment_breakdown
        ],
    }


@router.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(ws)
    try:
        while True:
            low_stock_items = (
                db.query(Product)
                .filter(Product.is_active == True, Product.quantity <= Product.reorder_level)
                .all()
            )
            if low_stock_items:
                alert = {
                    "type": "LOW_STOCK",
                    "count": len(low_stock_items),
                    "items": [
                        {"id": p.id, "name": p.name, "quantity": p.quantity, "reorder_level": p.reorder_level}
                        for p in low_stock_items[:5]
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await ws.send_json(alert)
            await asyncio.sleep(30)
    except (WebSocketDisconnect, Exception):
        manager.disconnect(ws)
