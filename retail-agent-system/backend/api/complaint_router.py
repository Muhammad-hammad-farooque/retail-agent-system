from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.complaint import Complaint, ComplaintStatus
from ..models.customer import Customer
from ..models.notification import Notification, NotificationType
from ..models.user import User
from ..auth.jwt_handler import get_current_user
from ..tools.email_tools import send_complaint_resolution_email

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("")
def get_all_complaints(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Complaint)
    if status:
        query = query.filter(Complaint.status == status)
    return query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()


@router.patch("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    status: ComplaintStatus,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint.status = status
    email_sent = False

    if status == ComplaintStatus.resolved:
        customer = db.query(Customer).filter(Customer.id == complaint.customer_id).first()
        if customer:
            email_sent = send_complaint_resolution_email(customer, complaint)
            notif = Notification(
                type=NotificationType.complaint,
                title="Complaint Resolved",
                message=f"Complaint {complaint.reference} resolved. "
                        + (f"Resolution email sent to {customer.email}." if email_sent else "No email on record."),
                reference_id=complaint.id,
                reference_type="complaint",
            )
            db.add(notif)

    db.commit()
    return {
        "complaint_id": complaint_id,
        "reference": complaint.reference,
        "status": complaint.status,
        "email_sent": email_sent,
    }
