import os
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from agents import function_tool
from ..database import SessionLocal
from ..models.product import Product
from ..models.sale import Sale
from ..models.promotion import Promotion
from ..models.customer import Customer
from ..models.notification import Notification, NotificationType
from ..tools.email_tools import send_single_email


def _db():
    return SessionLocal()


@function_tool
def get_sales_trends(days: int = 30, category: Optional[str] = None) -> str:
    """Get daily sales trends for the past N days, optionally filtered by category."""
    db = _db()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
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


@function_tool
def get_top_products(limit: int = 5, days: int = 30) -> str:
    """Get top-performing products by revenue for marketing focus."""
    db = _db()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
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


@function_tool
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


@function_tool
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
        promo = Promotion(
            product_id=product_id,
            discount_pct=discount_pct,
            original_price=product.price,
            promo_price=discounted_price,
            start_date=start_date,
            end_date=end_date,
        )
        db.add(promo)
        notif = Notification(
            type=NotificationType.promotion,
            title="New Promotion Created",
            message=f"{discount_pct}% off on {product.name} from {start_date} to {end_date}",
            reference_id=product_id,
            reference_type="product",
        )
        db.add(notif)
        db.commit()
        return (
            f"Promotion Created:\n"
            f"Product: {product.name}\n"
            f"Discount: {discount_pct}%\n"
            f"Original Price: Rs.{product.price:,.0f}\n"
            f"Promo Price: Rs.{discounted_price:,.0f}\n"
            f"Valid: {start_date} to {end_date}\n"
            f"Status: ACTIVE"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to create promotion: {str(e)}"
    finally:
        db.close()


@function_tool
def create_category_promotion(category: str, discount_pct: float, start_date: str, end_date: str) -> str:
    """Create a promotional discount for ALL products in a category at once.
    Use this when the user wants to apply a discount to an entire category (e.g. all Clothing items).
    discount_pct: 0-70. Products where the discount would go below cost price get the maximum safe discount instead."""
    db = _db()
    try:
        products = db.query(Product).filter(
            Product.category.ilike(f"%{category}%"),
            Product.is_active == True,
        ).all()

        if not products:
            return f"No active products found in category '{category}'."

        if not (0 < discount_pct <= 70):
            return "Discount must be between 1% and 70%."

        created = []
        skipped = []

        for product in products:
            effective_discount = discount_pct
            discounted_price = product.price * (1 - effective_discount / 100)

            if discounted_price < product.cost_price:
                max_safe = ((product.price - product.cost_price) / product.price) * 100
                if max_safe <= 0:
                    skipped.append(f"{product.name} (no margin)")
                    continue
                effective_discount = round(max_safe * 0.95, 1)
                discounted_price = product.price * (1 - effective_discount / 100)

            promo = Promotion(
                product_id=product.id,
                discount_pct=effective_discount,
                original_price=product.price,
                promo_price=discounted_price,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(promo)
            created.append(f"  {product.name}: {effective_discount}% off  Rs.{product.price:,.0f} -> Rs.{discounted_price:,.0f}")

        if created:
            db.add(Notification(
                type=NotificationType.promotion,
                title=f"Category Promotion: {category}",
                message=f"{discount_pct}% off on all {category} items from {start_date} to {end_date}. {len(created)} products included.",
                reference_id=None,
                reference_type="category",
            ))
            db.commit()

        lines = [
            f"Category Promotion Created: {category}",
            f"Requested Discount : {discount_pct}%",
            f"Valid              : {start_date} to {end_date}",
            f"Products Created   : {len(created)}",
        ]
        if created:
            lines.append("\nProducts included:")
            lines.extend(created)
        if skipped:
            lines.append(f"\nSkipped ({len(skipped)} products — zero margin):")
            lines.extend(f"  {s}" for s in skipped)

        return "\n".join(lines)

    except Exception as e:
        db.rollback()
        return f"Failed to create category promotion: {str(e)}"
    finally:
        db.close()


@function_tool
def send_promotional_email(
    subject: str,
    message: str,
    min_loyalty_points: int = 0,
    customer_name: Optional[str] = None,
) -> str:
    """Send a promotional email to customers.
    - customer_name: send to a specific customer only (partial name match, e.g. 'ahmed ali')
    - min_loyalty_points: filter by loyalty points (e.g. 500 for VIP only). Ignored if customer_name is set.
    - Leave both at default to send to all customers."""
    db = _db()
    try:
        query = db.query(Customer).filter(
            Customer.is_active == True,
            Customer.email.isnot(None),
        )

        if customer_name:
            query = query.filter(Customer.name.ilike(f"%{customer_name}%"))
        else:
            query = query.filter(Customer.loyalty_points >= min_loyalty_points)

        customers = query.all()

        if not customers:
            if customer_name:
                return f"No customer found matching '{customer_name}' with an email address on file."
            return f"No customers found with loyalty points >= {min_loyalty_points}."

        sent = 0
        failed = 0
        errors = []
        for customer in customers:
            personalized_body = f"Dear {customer.name},\n\n{message}\n\nYour Loyalty Points: {customer.loyalty_points}\n\nRegards,\nRetail Store Team"
            ok, err = send_single_email(customer.email, subject, personalized_body)
            if ok:
                sent += 1
            else:
                failed += 1
                errors.append(f"  {customer.name} ({customer.email}): {err}")

        target_label = f"Customer: {customer_name}" if customer_name else f"Loyalty Points >= {min_loyalty_points}"
        db.add(Notification(
            type=NotificationType.promotion,
            title="Promotional Email Campaign Sent",
            message=f"Email '{subject}' sent to {sent} customers ({target_label}). Failed: {failed}.",
            reference_id=None,
            reference_type="marketing",
        ))
        db.commit()

        result = (
            f"Promotional Email Campaign:\n"
            f"Subject        : {subject}\n"
            f"Target         : {target_label}\n"
            f"Total Customers: {len(customers)}\n"
            f"Emails Sent    : {sent}\n"
            f"Failed         : {failed}\n"
            f"Status         : {'SUCCESS' if failed == 0 else ('FAILED' if sent == 0 else 'PARTIAL')}"
        )
        if errors:
            result += "\n\nFailure Reasons:\n" + "\n".join(errors)
        return result
    except Exception as e:
        db.rollback()
        return f"Failed to send promotional emails: {str(e)}"
    finally:
        db.close()


@function_tool
def send_promotional_sms(message: str, min_loyalty_points: int = 0) -> str:
    """Send a promotional SMS to customers via Twilio. Optionally filter by minimum loyalty points. Use 0 to send to all customers."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not from_number:
        return "Twilio credentials not configured. Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER to your .env file."

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
    except ImportError:
        return "Twilio package not installed. Run: pip install twilio"

    db = _db()
    try:
        customers = db.query(Customer).filter(
            Customer.is_active == True,
            Customer.phone != None,
            Customer.loyalty_points >= min_loyalty_points,
        ).all()

        if not customers:
            return f"No customers found with phone numbers and loyalty points >= {min_loyalty_points}."

        sent = 0
        failed = 0
        for customer in customers:
            try:
                client.messages.create(
                    body=f"Hi {customer.name}! {message}",
                    from_=from_number,
                    to=customer.phone,
                )
                sent += 1
            except Exception:
                failed += 1

        db.add(Notification(
            type=NotificationType.promotion,
            title="Promotional SMS Campaign Sent",
            message=f"SMS sent to {sent} customers (min loyalty: {min_loyalty_points} pts). Failed: {failed}.",
            reference_id=None,
            reference_type="marketing",
        ))
        db.commit()

        return (
            f"Promotional SMS Campaign:\n"
            f"Target Filter  : Loyalty Points >= {min_loyalty_points}\n"
            f"Total Customers: {len(customers)}\n"
            f"SMS Sent       : {sent}\n"
            f"Failed         : {failed}\n"
            f"Status         : {'SUCCESS' if failed == 0 else 'PARTIAL'}"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to send promotional SMS: {str(e)}"
    finally:
        db.close()


@function_tool
def generate_marketing_report() -> str:
    """Generate a comprehensive marketing performance report."""
    db = _db()
    try:
        now = datetime.now(timezone.utc)
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
