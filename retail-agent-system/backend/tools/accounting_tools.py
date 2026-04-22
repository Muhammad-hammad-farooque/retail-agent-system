from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from ..database import SessionLocal
from ..models.invoice import Invoice, InvoiceItem, InvoiceStatus
from ..models.product import Product
from ..models.customer import Customer
from ..models.sale import Sale


def _db():
    return SessionLocal()


def get_invoice(invoice_id: int) -> str:
    """Get full details of a specific invoice by ID."""
    db = _db()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            return f"Invoice with ID {invoice_id} not found."
        lines = [
            f"Invoice: {inv.invoice_number}",
            f"Status: {inv.status.value.upper()}",
            f"Customer ID: {inv.customer_id or 'Walk-in'}",
            f"Payment: {inv.payment_method or 'N/A'}",
            f"Date: {inv.created_at.strftime('%Y-%m-%d')}",
            f"Total Amount: Rs.{inv.total_amount:,.0f}",
            f"Discount: Rs.{inv.discount:,.0f}",
            f"Tax (GST): Rs.{inv.tax:,.0f}",
            f"Net Amount: Rs.{inv.net_amount:,.0f}",
            f"\nItems ({len(inv.items)}):",
        ]
        for item in inv.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            name = product.name if product else f"Product #{item.product_id}"
            lines.append(f"  - {name}: {item.quantity} x Rs.{item.unit_price:,.0f} = Rs.{item.subtotal:,.0f}")
        return "\n".join(lines)
    finally:
        db.close()


def get_financial_summary(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Get financial summary for a date range (format: YYYY-MM-DD). Defaults to current month."""
    db = _db()
    try:
        now = datetime.utcnow()
        start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else now.replace(day=1)
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else now

        invoices = db.query(Invoice).filter(
            Invoice.created_at >= start,
            Invoice.created_at <= end,
        ).all()

        paid = [i for i in invoices if i.status == InvoiceStatus.paid]
        total_revenue = sum(i.net_amount for i in paid)
        total_tax = sum(i.tax for i in paid)
        total_discount = sum(i.discount for i in invoices)

        return (
            f"Financial Summary ({start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}):\n"
            f"Total Invoices: {len(invoices)}\n"
            f"Paid Invoices: {len(paid)}\n"
            f"Pending: {len([i for i in invoices if i.status == InvoiceStatus.pending])}\n"
            f"Cancelled: {len([i for i in invoices if i.status == InvoiceStatus.cancelled])}\n"
            f"Total Revenue (paid): Rs.{total_revenue:,.0f}\n"
            f"Total Tax Collected: Rs.{total_tax:,.0f}\n"
            f"Total Discounts Given: Rs.{total_discount:,.0f}"
        )
    finally:
        db.close()


def calculate_profit_loss(days: int = 30) -> str:
    """Calculate profit and loss for the past N days."""
    db = _db()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        sales = db.query(Sale).filter(Sale.sale_date >= since).all()
        total_revenue = sum(s.revenue for s in sales)
        total_profit = sum(s.profit for s in sales)
        total_cost = total_revenue - total_profit
        margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

        return (
            f"Profit & Loss — Last {days} days:\n"
            f"Total Revenue: Rs.{total_revenue:,.0f}\n"
            f"Total Cost: Rs.{total_cost:,.0f}\n"
            f"Gross Profit: Rs.{total_profit:,.0f}\n"
            f"Profit Margin: {margin:.1f}%"
        )
    finally:
        db.close()


def get_revenue_by_category(days: int = 30) -> str:
    """Get revenue breakdown by product category for the past N days."""
    db = _db()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        results = (
            db.query(Sale.category, func.sum(Sale.revenue).label("revenue"), func.sum(Sale.profit).label("profit"))
            .filter(Sale.sale_date >= since)
            .group_by(Sale.category)
            .order_by(func.sum(Sale.revenue).desc())
            .all()
        )
        if not results:
            return "No sales data found."
        lines = [f"Revenue by Category — Last {days} days:"]
        for cat, revenue, profit in results:
            margin = (profit / revenue * 100) if revenue else 0
            lines.append(f"  {cat}: Rs.{revenue:,.0f} revenue | Rs.{profit:,.0f} profit ({margin:.1f}%)")
        return "\n".join(lines)
    finally:
        db.close()


def get_top_selling_products(limit: int = 10, days: int = 30) -> str:
    """Get top selling products by revenue for the past N days."""
    db = _db()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        results = (
            db.query(Sale.product_id, func.sum(Sale.revenue).label("revenue"), func.sum(Sale.quantity_sold).label("units"))
            .filter(Sale.sale_date >= since)
            .group_by(Sale.product_id)
            .order_by(func.sum(Sale.revenue).desc())
            .limit(limit)
            .all()
        )
        if not results:
            return "No sales data available."
        lines = [f"Top {limit} Products by Revenue — Last {days} days:"]
        for pid, revenue, units in results:
            product = db.query(Product).filter(Product.id == pid).first()
            name = product.name if product else f"Product #{pid}"
            lines.append(f"  {name}: Rs.{revenue:,.0f} | {units} units sold")
        return "\n".join(lines)
    finally:
        db.close()
