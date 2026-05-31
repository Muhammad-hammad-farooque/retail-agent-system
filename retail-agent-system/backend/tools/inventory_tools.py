import time
from datetime import datetime, timezone
from typing import Optional
from agents import function_tool
from ..database import SessionLocal
from ..models.product import Product
from ..models.supplier import Supplier
from ..models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from ..models.invoice import Invoice, InvoiceItem, InvoiceStatus
from ..models.sale import Sale
from ..models.notification import Notification, NotificationType
from ..tools.email_tools import send_vendor_email

BUDGET_THRESHOLD = 100_000


def _db():
    return SessionLocal()


@function_tool
def check_stock(product_id: int) -> str:
    """Check current stock level of a product by its ID."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
        status = "LOW STOCK" if product.quantity <= product.reorder_level else "OK"
        return (
            f"Product: {product.name} (SKU: {product.sku})\n"
            f"Category: {product.category}\n"
            f"Quantity: {product.quantity} units\n"
            f"Reorder Level: {product.reorder_level}\n"
            f"Status: {status}"
        )
    finally:
        db.close()


@function_tool
def update_stock(product_id: int, quantity_change: int) -> str:
    """Update stock level of a product. Use positive value to add stock, negative to deduct."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
        old_qty = product.quantity
        new_qty = old_qty + quantity_change
        if new_qty < 0:
            return f"Cannot deduct {abs(quantity_change)} units — only {old_qty} in stock."
        product.quantity = new_qty
        db.commit()
        action = "Added" if quantity_change > 0 else "Deducted"
        return (
            f"{action} {abs(quantity_change)} units for {product.name}.\n"
            f"Stock: {old_qty} → {new_qty} units."
        )
    finally:
        db.close()


@function_tool
def get_low_stock_alerts(threshold: Optional[int] = None) -> str:
    """Get all products that are at or below their reorder level (or a custom threshold)."""
    db = _db()
    try:
        query = db.query(Product).filter(Product.is_active == True)
        if threshold is not None:
            query = query.filter(Product.quantity <= threshold)
        else:
            query = query.filter(Product.quantity <= Product.reorder_level)
        products = query.order_by(Product.quantity.asc()).all()
        if not products:
            return "No low stock alerts. All products are sufficiently stocked."
        lines = [f"LOW STOCK ALERTS ({len(products)} products):"]
        for p in products:
            lines.append(f"- {p.name} (SKU: {p.sku}): {p.quantity} units (Reorder Level: {p.reorder_level})")
        return "\n".join(lines)
    finally:
        db.close()


@function_tool
def add_product(
    name: str,
    sku: str,
    category: str,
    price: float,
    cost_price: float,
    quantity: int,
    reorder_level: int = 10,
    supplier: Optional[str] = None,
) -> str:
    """Add a new product to the inventory."""
    db = _db()
    try:
        if db.query(Product).filter(Product.sku == sku).first():
            return f"Product with SKU '{sku}' already exists."
        product = Product(
            name=name, sku=sku, category=category,
            price=price, cost_price=cost_price,
            quantity=quantity, reorder_level=reorder_level,
            supplier=supplier,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return f"Product '{name}' added successfully with ID {product.id}."
    finally:
        db.close()


@function_tool
def create_purchase_order(product_id: int, quantity: int) -> str:
    """Create a purchase order for restocking a product. Auto-approves and emails vendor if total is under Rs.100,000. Requires manager approval above that."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."

        # Duplicate check — skip if open PO exists for this product today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        existing = db.query(PurchaseOrder).filter(
            PurchaseOrder.product_id == product_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.pending,
                PurchaseOrderStatus.approved,
                PurchaseOrderStatus.sent_to_vendor,
            ]),
            PurchaseOrder.created_at >= today_start,
        ).first()
        if existing:
            return (
                f"Purchase Order Already Exists (not duplicated):\n"
                f"Order Number : {existing.order_number}\n"
                f"Product      : {product.name}\n"
                f"Quantity     : {existing.quantity} units\n"
                f"Total Cost   : Rs.{existing.total_cost:,.0f}\n"
                f"Status       : {existing.status.value.upper()}"
            )

        unit_cost = product.price
        total_cost = unit_cost * quantity
        order_number = f"PO-{product_id}-{time.strftime('%Y%m%d%H%M%S')}"

        # Auto-link supplier
        supplier_id = None
        supplier_obj = None
        if product.supplier:
            sup = db.query(Supplier).filter(
                Supplier.name.ilike(f"%{product.supplier}%"),
                Supplier.is_active == True,
            ).first()
            if sup:
                supplier_id = sup.id
                supplier_obj = sup

        po = PurchaseOrder(
            order_number=order_number,
            product_id=product_id,
            supplier_id=supplier_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            supplier=product.supplier,
        )
        db.add(po)
        db.flush()

        if total_cost <= BUDGET_THRESHOLD:
            # Auto-approve and email vendor
            email_sent = False
            if supplier_obj and supplier_obj.email:
                email_sent = send_vendor_email(supplier_obj, po)
                if email_sent:
                    po.status = PurchaseOrderStatus.sent_to_vendor
                    approval_note = f"Auto-approved & email sent to {supplier_obj.name} ({supplier_obj.email})"
                else:
                    po.status = PurchaseOrderStatus.approved
                    approval_note = f"Auto-approved but EMAIL FAILED for {supplier_obj.name} ({supplier_obj.email}) — check SMTP credentials on Render"
            else:
                po.status = PurchaseOrderStatus.approved
                approval_note = "Auto-approved (no supplier email on record — send manually)"

            db.add(Notification(
                type=NotificationType.purchase_order,
                title="Purchase Order Auto-Approved",
                message=f"PO {order_number} for {product.name} — {approval_note}",
                reference_id=product_id,
                reference_type="product",
            ))
            db.commit()
            return (
                f"Purchase Order Created & Auto-Approved:\n"
                f"Order Number : {order_number}\n"
                f"Product      : {product.name} (SKU: {product.sku})\n"
                f"Supplier     : {product.supplier or 'Not specified'}{' (linked)' if supplier_id else ''}\n"
                f"Quantity     : {quantity} units\n"
                f"Unit Cost    : Rs.{product.cost_price:,.0f}\n"
                f"Total Cost   : Rs.{total_cost:,.0f}\n"
                f"Status       : {po.status.value.upper()}\n"
                f"Approval     : {approval_note}"
            )
        else:
            # Over budget — leave pending for manager
            db.add(Notification(
                type=NotificationType.purchase_order,
                title="Purchase Order Pending — Manager Approval Required",
                message=f"PO {order_number} for Rs.{total_cost:,.0f} exceeds Rs.100,000. Manager approval required.",
                reference_id=product_id,
                reference_type="product",
            ))
            db.commit()
            return (
                f"Purchase Order Created — Manager Approval Required:\n"
                f"Order Number : {order_number}\n"
                f"Product      : {product.name} (SKU: {product.sku})\n"
                f"Supplier     : {product.supplier or 'Not specified'}{' (linked)' if supplier_id else ''}\n"
                f"Quantity     : {quantity} units\n"
                f"Unit Cost    : Rs.{product.cost_price:,.0f}\n"
                f"Total Cost   : Rs.{total_cost:,.0f}\n"
                f"Status       : PENDING APPROVAL\n"
                f"Note         : Total exceeds Rs.100,000 — go to Purchase Orders page to approve."
            )
    except Exception as e:
        db.rollback()
        return f"Failed to create purchase order: {str(e)}"
    finally:
        db.close()


@function_tool
def search_product_by_name(name: str) -> str:
    """Search products by name (partial, case-insensitive). Returns matching products with their IDs so you can use them in other tools."""
    db = _db()
    try:
        products = db.query(Product).filter(
            Product.name.ilike(f"%{name}%"),
            Product.is_active == True,
        ).all()
        if not products:
            return f"No active products found matching '{name}'."
        lines = [f"Products matching '{name}' ({len(products)} found):"]
        for p in products:
            status = "LOW STOCK" if p.quantity <= p.reorder_level else "OK"
            lines.append(
                f"- ID: {p.id} | [{p.sku}] {p.name} | Category: {p.category} | "
                f"Stock: {p.quantity} units | Reorder Level: {p.reorder_level} | "
                f"Cost: Rs.{p.cost_price:,.0f} | Status: {status}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@function_tool
def receive_purchase_order(product_id: int, quantity_received: int) -> str:
    """Mark a purchase order as received and update product stock in one step.
    Use this when the user says goods/stock/order has arrived or been received."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."

        # Only accept POs that have been sent to vendor — pending/approved are not eligible
        po = (
            db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.product_id == product_id,
                PurchaseOrder.status == PurchaseOrderStatus.sent_to_vendor,
            )
            .order_by(PurchaseOrder.created_at.desc())
            .first()
        )

        if not po:
            return (
                f"No active Purchase Order found for {product.name} with status 'Sent to Vendor'.\n"
                f"Goods can only be received against a purchase order that has already been sent to the vendor.\n"
                f"Please create a purchase order first, wait for it to be sent to vendor, then mark it received."
            )

        # Quantity mismatch check
        mismatch_note = ""
        if quantity_received != po.quantity:
            diff = quantity_received - po.quantity
            if diff > 0:
                mismatch_note = (
                    f"\nWARNING — Over-delivery: PO was for {po.quantity} units but "
                    f"{quantity_received} received (+{diff} extra). Stock updated with actual received quantity."
                )
            else:
                mismatch_note = (
                    f"\nWARNING — Short delivery: PO was for {po.quantity} units but "
                    f"only {quantity_received} received ({diff} short). Stock updated with actual received quantity."
                )

        # Update stock
        old_qty = product.quantity
        product.quantity = old_qty + quantity_received
        po.status = PurchaseOrderStatus.received

        notif = Notification(
            type=NotificationType.purchase_order,
            title="Stock Received",
            message=f"Received {quantity_received} units of {product.name} (PO qty: {po.quantity}). Stock: {old_qty} → {product.quantity}",
            reference_id=product_id,
            reference_type="product",
        )
        db.add(notif)
        db.commit()

        return (
            f"Order Received — All Updated:\n"
            f"Product        : {product.name} (SKU: {product.sku})\n"
            f"PO Quantity    : {po.quantity} units\n"
            f"Qty Received   : {quantity_received} units\n"
            f"Stock          : {old_qty} → {product.quantity} units\n"
            f"Purchase Order : {po.order_number} → RECEIVED"
            f"{mismatch_note}"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to process received order: {str(e)}"
    finally:
        db.close()


@function_tool
def sell_product(
    product_id: int,
    quantity: int,
    payment_method: str = "Cash",
    customer_id: Optional[int] = None,
) -> str:
    """Process a sale: deducts stock and creates a paid invoice + sale record.
    Payment methods: Cash, Card, EasyPaisa, JazzCash, Bank Transfer."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
        if product.quantity < quantity:
            return (
                f"Insufficient stock. Only {product.quantity} units of {product.name} available. "
                f"Cannot sell {quantity} units."
            )

        # Deduct stock
        old_qty = product.quantity
        product.quantity = old_qty - quantity

        # Calculate amounts (17% GST)
        total_amount = product.price * quantity
        tax = round(total_amount * 0.17, 2)
        net_amount = round(total_amount + tax, 2)
        profit = round((product.price - product.cost_price) * quantity, 2)

        # Create Invoice
        invoice_number = f"INV-{time.strftime('%Y%m%d%H%M%S')}-{product_id}"
        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=customer_id,
            total_amount=round(total_amount, 2),
            discount=0.0,
            tax=tax,
            net_amount=net_amount,
            status=InvoiceStatus.paid,
            payment_method=payment_method,
        )
        db.add(invoice)
        db.flush()

        # Create InvoiceItem
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.price,
            subtotal=round(total_amount, 2),
        ))

        # Create Sale record (for accounting/reporting)
        db.add(Sale(
            product_id=product_id,
            quantity_sold=quantity,
            revenue=round(total_amount, 2),
            profit=profit,
            category=product.category,
        ))

        db.commit()

        low_stock_warning = ""
        if product.quantity <= product.reorder_level:
            low_stock_warning = f"\nWARNING: Stock is now low ({product.quantity} units). Consider creating a purchase order."

        return (
            f"Sale Processed Successfully:\n"
            f"Invoice       : {invoice_number}\n"
            f"Product       : {product.name} (SKU: {product.sku})\n"
            f"Quantity Sold : {quantity} units\n"
            f"Unit Price    : Rs.{product.price:,.0f}\n"
            f"Total Amount  : Rs.{total_amount:,.0f}\n"
            f"Tax (17% GST) : Rs.{tax:,.0f}\n"
            f"Net Amount    : Rs.{net_amount:,.0f}\n"
            f"Payment       : {payment_method}\n"
            f"Stock         : {old_qty} → {product.quantity} units\n"
            f"Status        : PAID"
            f"{low_stock_warning}"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to process sale: {str(e)}"
    finally:
        db.close()


@function_tool
def update_price(product_id: int, new_price: float) -> str:
    """Update the base selling price of a product. Use when supplier cost changes or market price adjustment is needed."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
        if new_price <= 0:
            return "Price must be greater than zero."
        if new_price < product.cost_price:
            return (
                f"Cannot set price to Rs.{new_price:,.0f} — below cost price Rs.{product.cost_price:,.0f}. "
                f"Minimum selling price must be above cost."
            )
        old_price = product.price
        product.price = new_price
        db.commit()
        change_pct = ((new_price - old_price) / old_price) * 100
        return (
            f"Price Updated: {product.name}\n"
            f"Old Price : Rs.{old_price:,.0f}\n"
            f"New Price : Rs.{new_price:,.0f}\n"
            f"Change    : {change_pct:+.1f}%"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to update price: {str(e)}"
    finally:
        db.close()


@function_tool
def list_products_by_category(category: str) -> str:
    """List all active products in a given category."""
    db = _db()
    try:
        products = db.query(Product).filter(
            Product.category == category, Product.is_active == True
        ).all()
        if not products:
            return f"No products found in category '{category}'."
        lines = [f"Products in '{category}' ({len(products)} total):"]
        for p in products:
            lines.append(f"- [{p.sku}] {p.name} | Price: Rs.{p.price:,.0f} | Stock: {p.quantity}")
        return "\n".join(lines)
    finally:
        db.close()
