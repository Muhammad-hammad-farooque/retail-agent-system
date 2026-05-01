from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.complaint import Complaint, ComplaintStatus
from ..models.user import User
from ..auth.jwt_handler import get_current_user

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
    db.commit()
    return {"complaint_id": complaint_id, "status": complaint.status}
