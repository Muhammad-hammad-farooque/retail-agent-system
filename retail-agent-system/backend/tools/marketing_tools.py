from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from ..database import SessionLocal
from ..models.product import Product
from ..models.sale import Sale


def _db():
    return SessionLocal()


def get_sales_trends(days: int = 30, category: Optional[str] = None) -> str:
    """Get daily sales trends for the past N days, optionally filtered by category."""
    db = _db()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        query = db.query(
            func.date(Sale.sale_date).label("date"),
            func.sum(Sale.revenue).label("revenue"),
            func.sum(Sale.quantity_sold).label("units"),
        ).filter(Sale.sale_date >= since)
        if category:
            query = query.filter(Sale.category == category)
        results = query.group_by(func.date(Sale.sale_date)).order_by(func.date(Sale.sale_date)).all()

        if not results:
            return "No sales data found for this period."

        total_rev = sum(r.revenue for r in results)
        avg_daily = total_rev / days
        lines = [f"Sales Trends — Last {days} days{' | ' + category if category else ''}:"]
        lines.append(f"Total Revenue: Rs.{total_rev:,.0f} | Avg Daily: Rs.{avg_daily:,.0f}")
        lines.append("\nDaily Breakdown (last 7 days):")
        for row in results[-7:]:
            lines.append(f"  {row.date}: Rs.{row.revenue:,.0f} | {row.units} units")
        return "\n".join(lines)
    finally:
        db.close()


def get_top_products(limit: int = 5, days: int = 30) -> str:
    """Get top-performing products by revenue for marketing focus."""
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
            return "No product sales data available."
        lines = [f"Top {limit} Products for Marketing (Last {days} days):"]
        for pid, revenue, units in results:
            product = db.query(Product).filter(Product.id == pid).first()
            name = product.name if product else f"Product #{pid}"
            category = product.category if product else "Unknown"
            lines.append(f"  {name} ({category}): Rs.{revenue:,.0f} | {units} units")
        return "\n".join(lines)
    finally:
        db.close()


def update_price(product_id: int, new_price: float) -> str:
    """Update the selling price of a product."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
        if new_price <= 0:
            return "Price must be greater than zero."
        if new_price < product.cost_price:
            return (
                f"Warning: New price Rs.{new_price:,.0f} is below cost price Rs.{product.cost_price:,.0f}. "
                f"This will result in a loss. Price NOT updated."
            )
        old_price = product.price
        product.price = new_price
        db.commit()
        change_pct = ((new_price - old_price) / old_price) * 100
        return (
            f"Price updated for {product.name}:\n"
            f"Old Price: Rs.{old_price:,.0f}\n"
            f"New Price: Rs.{new_price:,.0f}\n"
            f"Change: {change_pct:+.1f}%"
        )
    finally:
        db.close()


def create_promotion(product_id: int, discount_pct: float, start_date: str, end_date: str) -> str:
    """Create a promotional discount for a product (discount_pct: 0-100)."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
        if not (0 < discount_pct <= 70):
            return "Discount must be between 1% and 70%."
        discounted_price = product.price * (1 - discount_pct / 100)
        if discounted_price < product.cost_price:
            return (
                f"Discount of {discount_pct}% would price the product below cost. "
                f"Maximum allowed discount: {((product.price - product.cost_price) / product.price * 100):.1f}%"
            )
        return (
            f"Promotion Created:\n"
            f"Product: {product.name}\n"
            f"Discount: {discount_pct}%\n"
            f"Original Price: Rs.{product.price:,.0f}\n"
            f"Promo Price: Rs.{discounted_price:,.0f}\n"
            f"Valid: {start_date} to {end_date}\n"
            f"Status: ACTIVE"
        )
    finally:
        db.close()


def generate_marketing_report() -> str:
    """Generate a comprehensive marketing performance report."""
    db = _db()
    try:
        now = datetime.utcnow()
        last_30 = now - timedelta(days=30)
        last_7 = now - timedelta(days=7)

        rev_30 = db.query(func.sum(Sale.revenue)).filter(Sale.sale_date >= last_30).scalar() or 0
        rev_7 = db.query(func.sum(Sale.revenue)).filter(Sale.sale_date >= last_7).scalar() or 0

        top_cat = (
            db.query(Sale.category, func.sum(Sale.revenue).label("rev"))
            .filter(Sale.sale_date >= last_30)
            .group_by(Sale.category)
            .order_by(func.sum(Sale.revenue).desc())
            .first()
        )

        low_margin = (
            db.query(Product)
            .filter(Product.is_active == True)
            .all()
        )
        low_margin_products = [p for p in low_margin if p.cost_price > 0 and ((p.price - p.cost_price) / p.price) < 0.15]

        lines = [
            "=== MARKETING PERFORMANCE REPORT ===",
            f"Generated: {now.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"Revenue Last 7 Days:  Rs.{rev_7:,.0f}",
            f"Revenue Last 30 Days: Rs.{rev_30:,.0f}",
            f"Best Category: {top_cat[0] if top_cat else 'N/A'} (Rs.{top_cat[1]:,.0f})" if top_cat else "Best Category: N/A",
            "",
            f"Low Margin Products ({len(low_margin_products)} items < 15% margin):",
        ]
        for p in low_margin_products[:5]:
            margin = ((p.price - p.cost_price) / p.price) * 100
            lines.append(f"  - {p.name}: {margin:.1f}% margin")

        lines.append("\nRecommendation: Focus promotions on top category and review low-margin products.")
        return "\n".join(lines)
    finally:
        db.close()
