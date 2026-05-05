from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from ..database import SessionLocal
from ..models.invoice import Invoice, InvoiceItem, InvoiceStatus
from ..models.product import Product
from ..models.customer import Customer
from ..models.sale import Sale
from ..models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from ..models.supplier import Supplier
from ..models.notification import Notification, NotificationType
from ..tools.email_tools import send_vendor_email


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


def approve_purchase_order(po_id: int) -> str:
    """Approve a pending purchase order. Automatically sends an email to the vendor if supplier email is on record."""
    db = _db()
    try:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return f"Purchase Order with ID {po_id} not found."
        if po.status != PurchaseOrderStatus.pending:
            return f"Cannot approve — PO {po.order_number} is already '{po.status.value}'."
        if po.total_cost > 100000:
            return (
                f"BUDGET ALERT: PO {po.order_number} total cost is Rs.{po.total_cost:,.0f} "
                f"which exceeds Rs.100,000. Manager sign-off required before approval."
            )

        email_sent = False
        supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first() if po.supplier_id else None

        if supplier and supplier.email:
            email_sent = send_vendor_email(supplier, po)
            po.status = PurchaseOrderStatus.sent_to_vendor
            notif_msg = f"PO {po.order_number} approved and emailed to {supplier.name} ({supplier.email})"
        else:
            po.status = PurchaseOrderStatus.approved
            notif_msg = f"PO {po.order_number} approved. No supplier email on record — send manually."

        notif = Notification(
            type=NotificationType.purchase_order,
            title="Purchase Order Approved",
            message=notif_msg,
            reference_id=po.id,
            reference_type="purchase_order",
        )
        db.add(notif)
        db.commit()

        return (
            f"Purchase Order Approved:\n"
            f"Order Number  : {po.order_number}\n"
            f"Product       : {po.product.name} (SKU: {po.product.sku})\n"
            f"Quantity      : {po.quantity} units\n"
            f"Total Cost    : Rs.{po.total_cost:,.0f}\n"
            f"Supplier      : {supplier.name if supplier else po.supplier or 'Not specified'}\n"
            f"Status        : {po.status.value.upper()}\n"
            f"Vendor Email  : {'Sent to ' + supplier.email if email_sent else 'Not sent (no email on record)'}"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to approve purchase order: {str(e)}"
    finally:
        db.close()


def reject_purchase_order(po_id: int, reason: str) -> str:
    """Reject a purchase order with a reason."""
    db = _db()
    try:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return f"Purchase Order with ID {po_id} not found."
        if po.status not in (PurchaseOrderStatus.pending, PurchaseOrderStatus.approved):
            return f"Cannot reject — PO {po.order_number} is already '{po.status.value}'."

        po.status = PurchaseOrderStatus.rejected
        po.notes = f"REJECTED: {reason}"
        notif = Notification(
            type=NotificationType.purchase_order,
            title="Purchase Order Rejected",
            message=f"PO {po.order_number} rejected. Reason: {reason}",
            reference_id=po.id,
            reference_type="purchase_order",
        )
        db.add(notif)
        db.commit()

        return (
            f"Purchase Order Rejected:\n"
            f"Order Number : {po.order_number}\n"
            f"Product      : {po.product.name}\n"
            f"Total Cost   : Rs.{po.total_cost:,.0f}\n"
            f"Reason       : {reason}\n"
            f"Status       : REJECTED"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to reject purchase order: {str(e)}"
    finally:
        db.close()
