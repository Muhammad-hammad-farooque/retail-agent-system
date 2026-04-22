from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import asyncio
import json

from ..database import get_db
from ..models.product import Product
from ..models.invoice import Invoice, InvoiceStatus
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
    today = datetime.utcnow()
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


@router.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(ws)
    try:
        while True:
            # Check for low stock every 30 seconds and push alerts
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
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await ws.send_json(alert)
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(ws)
