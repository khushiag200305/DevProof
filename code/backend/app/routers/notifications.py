"""The signed-in user's notifications (the bell in the top bar)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user
from ..services.notifications import as_dict

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

SHOWN = 30


@router.get("")
def list_notifications(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """The newest notifications and how many are unread."""
    base = db.query(models.Notification).filter_by(user_id=user.user_id)
    items = base.order_by(models.Notification.created_at.desc(), models.Notification.notification_id.desc()).limit(SHOWN).all()
    unread = base.filter(models.Notification.read_at.is_(None)).count()
    return {"unread": unread, "items": [as_dict(n) for n in items]}


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    note = db.query(models.Notification).filter_by(notification_id=notification_id, user_id=user.user_id).first()
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.")
    if note.read_at is None:
        note.read_at = datetime.now(timezone.utc)
        db.commit()
    return as_dict(note)


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.user_id, models.Notification.read_at.is_(None)
    ).update({"read_at": datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    return {"unread": 0}
