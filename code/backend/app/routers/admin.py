"""
Admin-only: approve or reject recruiter accounts. Admins are the emails
listed in ADMIN_EMAILS in the backend .env (see app/services/approval.py).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import require_admin
from ..services import notifications
from ..services.approval import PENDING, STATUSES, effective_status, is_admin_email

router = APIRouter(prefix="/api/admin", tags=["admin"])

_ORDER = {PENDING: 0, "approved": 1, "rejected": 2}


class StatusIn(BaseModel):
    status: str


def _recruiter_dict(user: models.User) -> dict:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "picture_url": user.picture_url,
        "domain": user.email.rsplit("@", 1)[-1],
        "created_at": user.created_at,
        "status": effective_status(user),
    }


@router.get("/recruiters")
def list_recruiters(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    """Every recruiter account except admins: waiting ones first, newest first."""
    recruiters = [
        u for u in db.query(models.User).filter_by(role="recruiter").all() if not is_admin_email(u.email)
    ]
    recruiters.sort(key=lambda u: (_ORDER[effective_status(u)], -u.created_at.timestamp()))
    return [_recruiter_dict(u) for u in recruiters]


@router.put("/recruiters/{user_id}")
def set_recruiter_status(
    user_id: int,
    body: StatusIn,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    """Approve, reject, or send a recruiter back to waiting."""
    if body.status not in STATUSES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Status must be pending, approved or rejected.")
    user = db.query(models.User).filter_by(user_id=user_id, role="recruiter").first()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recruiter not found.")
    if is_admin_email(user.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins are always approved.")
    user.recruiter_status = body.status
    if body.status == "approved":
        notifications.recruiter_approved(db, user)
    db.commit()
    return _recruiter_dict(user)
