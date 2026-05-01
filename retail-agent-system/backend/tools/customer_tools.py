import time
from typing import Optional
from ..database import SessionLocal
from ..models.customer import Customer
from ..models.invoice import Invoice, InvoiceStatus
from ..models.complaint import Complaint
from ..models.notification import Notification, NotificationType
from ..rag.pipeline import rag_pipeline


def _db():
    return SessionLocal()


def get_customer_info(customer_id: int) -> str:
    """Get customer profile information by customer ID."""
    db = _db()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return f"Customer with ID {customer_id} not found."
        # Mask sensitive PII — guardrails will also enforce this
        phone_masked = f"****{customer.phone[-4:]}" if customer.phone and len(customer.phone) >= 4 else "N/A"
        address_masked = customer.address[:10] + "..." if customer.address else "N/A"
        return (
            f"Customer Profile:\n"
            f"ID: {customer.id}\n"
            f"Name: {customer.name}\n"
            f"Email: {customer.email}\n"
            f"Phone: {phone_masked}\n"
            f"Address: {address_masked}\n"
            f"Loyalty Points: {customer.loyalty_points}\n"
            f"Total Spent: Rs.{customer.total_spent:,.0f}\n"
            f"Status: {'Active' if customer.is_active else 'Inactive'}"
        )
    finally:
        db.close()


def get_order_history(customer_id: int, limit: int = 10) -> str:
    """Get recent order/invoice history for a customer."""
    db = _db()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return f"Customer with ID {customer_id} not found."
        invoices = (
            db.query(Invoice)
            .filter(Invoice.customer_id == customer_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
            .all()
        )
        if not invoices:
            return f"No orders found for customer {customer.name}."
        lines = [f"Order History for {customer.name} (last {len(invoices)} orders):"]
        for inv in invoices:
            lines.append(
                f"  [{inv.invoice_number}] {inv.created_at.strftime('%Y-%m-%d')} | "
                f"Rs.{inv.net_amount:,.0f} | {inv.status.value.upper()} | {inv.payment_method or 'N/A'}"
            )
        total = sum(i.net_amount for i in invoices if i.status == InvoiceStatus.paid)
        lines.append(f"\nTotal Paid (shown): Rs.{total:,.0f}")
        return "\n".join(lines)
    finally:
        db.close()


def update_loyalty_points(customer_id: int, points_change: int) -> str:
    """Add or deduct loyalty points for a customer. Use negative value to deduct."""
    db = _db()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return f"Customer with ID {customer_id} not found."
        old_points = customer.loyalty_points
        new_points = old_points + points_change
        if new_points < 0:
            return f"Cannot deduct {abs(points_change)} points — customer only has {old_points} points."
        customer.loyalty_points = new_points
        db.commit()
        action = "Added" if points_change > 0 else "Deducted"
        return f"{action} {abs(points_change)} loyalty points for {customer.name}. Balance: {old_points} → {new_points} points."
    finally:
        db.close()


def search_customer_by_name(name: str) -> str:
    """Search for customers by name (partial match)."""
    db = _db()
    try:
        customers = db.query(Customer).filter(Customer.name.ilike(f"%{name}%")).limit(10).all()
        if not customers:
            return f"No customers found matching '{name}'."
        lines = [f"Customers matching '{name}':"]
        for c in customers:
            lines.append(f"  ID {c.id}: {c.name} | {c.email} | Points: {c.loyalty_points}")
        return "\n".join(lines)
    finally:
        db.close()


def search_faq(query: str) -> str:
    """Search the store FAQ knowledge base for answers to customer questions. Uses semantic search."""
    chunks = rag_pipeline.search(query, top_k=3)
    if not chunks:
        return "No relevant FAQ information found. Please contact customer support directly."
    lines = [f"FAQ Results for: '{query}'"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[{i}] (relevance: {chunk['relevance_score']:.2f})")
        lines.append(chunk["content"])
    return "\n".join(lines)


def handle_complaint(customer_id: int, complaint: str) -> str:
    """Log and acknowledge a customer complaint."""
    db = _db()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        name = customer.name if customer else f"Customer #{customer_id}"
        reference = f"COMP-{customer_id}-{time.strftime('%Y%m%d%H%M%S')}"
        record = Complaint(
            customer_id=customer_id,
            complaint=complaint,
            reference=reference,
        )
        db.add(record)
        notif = Notification(
            type=NotificationType.complaint,
            title="New Customer Complaint",
            message=f"{name}: {complaint[:100]}",
            reference_id=customer_id,
            reference_type="customer",
        )
        db.add(notif)
        db.commit()
        return (
            f"Complaint Registered for {name}:\n"
            f"Issue: {complaint}\n"
            f"Status: RECEIVED\n"
            f"Resolution: Our team will contact you within 24 hours.\n"
            f"Reference: {reference}"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to register complaint: {str(e)}"
    finally:
        db.close()
