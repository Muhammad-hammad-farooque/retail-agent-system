import time
from typing import Optional
from ..database import SessionLocal
from ..models.product import Product
from ..models.supplier import Supplier
from ..models.purchase_order import PurchaseOrder
from ..models.notification import Notification, NotificationType


def _db():
    return SessionLocal()


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


def create_purchase_order(product_id: int, quantity: int) -> str:
    """Create a purchase order request for restocking a product."""
    db = _db()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
        total_cost = product.cost_price * quantity
        order_number = f"PO-{product_id}-{time.strftime('%Y%m%d%H%M%S')}"

        # Auto-link supplier record by name match
        supplier_id = None
        if product.supplier:
            sup = db.query(Supplier).filter(
                Supplier.name.ilike(f"%{product.supplier}%"),
                Supplier.is_active == True,
            ).first()
            if sup:
                supplier_id = sup.id

        po = PurchaseOrder(
            order_number=order_number,
            product_id=product_id,
            supplier_id=supplier_id,
            quantity=quantity,
            unit_cost=product.cost_price,
            total_cost=total_cost,
            supplier=product.supplier,
        )
        db.add(po)
        notif = Notification(
            type=NotificationType.purchase_order,
            title="Purchase Order Created",
            message=f"PO {order_number} for {product.name} — {quantity} units from {product.supplier or 'supplier'}",
            reference_id=product_id,
            reference_type="product",
        )
        db.add(notif)
        db.commit()
        return (
            f"Purchase Order Created:\n"
            f"Order Number: {order_number}\n"
            f"Product: {product.name} (SKU: {product.sku})\n"
            f"Supplier: {product.supplier or 'Not specified'}{' (linked)' if supplier_id else ''}\n"
            f"Quantity to Order: {quantity} units\n"
            f"Unit Cost: Rs.{product.cost_price:,.0f}\n"
            f"Total Cost: Rs.{total_cost:,.0f}\n"
            f"Status: PENDING APPROVAL"
        )
    except Exception as e:
        db.rollback()
        return f"Failed to create purchase order: {str(e)}"
    finally:
        db.close()


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
