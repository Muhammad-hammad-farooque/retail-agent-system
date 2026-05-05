from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from ..models.supplier import Supplier
from ..models.notification import Notification, NotificationType
from ..models.user import User
from ..auth.jwt_handler import get_current_user
from ..tools.email_tools import send_vendor_email

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


@router.get("")
def get_all_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(PurchaseOrder)
    if status:
        query = query.filter(PurchaseOrder.status == status)
    return query.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{po_id}")
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.patch("/{po_id}/status")
def update_po_status(
    po_id: int,
    status: PurchaseOrderStatus,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    email_sent = False

    # When approved → auto-send email to vendor if supplier has email
    if status == PurchaseOrderStatus.approved and po.supplier_id:
        supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
        if supplier and supplier.email:
            email_sent = send_vendor_email(supplier, po)
            if email_sent:
                po.status = PurchaseOrderStatus.sent_to_vendor
                notif = Notification(
                    type=NotificationType.purchase_order,
                    title="Vendor Email Sent",
                    message=f"PO {po.order_number} approved and emailed to {supplier.name} ({supplier.email})",
                    reference_id=po.id,
                    reference_type="purchase_order",
                )
                db.add(notif)
            else:
                po.status = PurchaseOrderStatus.approved
        else:
            po.status = PurchaseOrderStatus.approved
    else:
        po.status = status

    db.commit()
    return {
        "po_id": po_id,
        "order_number": po.order_number,
        "status": po.status,
        "email_sent": email_sent,
    }
