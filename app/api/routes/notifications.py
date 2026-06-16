from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.notification import NotificationOut
from app.models.user import User
from app.core.security import require_auth, require_admin
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationOut])
def get_my_notifications(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return notification_service.get_user_notifications(db, current_user.id)


@router.post("/mark-read")
def mark_read(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    notification_service.mark_all_read_user(db, current_user.id)
    db.commit()
    return {"ok": True}


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return {"count": notification_service.unread_count_user(db, current_user.id)}


# ── Admin notifications ───────────────────────────────────────────

@router.get("/admin", response_model=List[NotificationOut])
def admin_notifications(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    return notification_service.get_admin_notifications(db)


@router.post("/admin/mark-read")
def admin_mark_read(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    notification_service.mark_all_read_admin(db)
    db.commit()
    return {"ok": True}
