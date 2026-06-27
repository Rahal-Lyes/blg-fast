from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.notification import NotificationOut
from app.models.user import User
from app.core.security import require_auth, require_admin
from app.services import notification_service
from fastapi import HTTPException

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ════════════════════════════════════════
#  USER NOTIFICATIONS
# ════════════════════════════════════════

@router.get("", response_model=List[NotificationOut])
def get_my_notifications(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return notification_service.get_user_notifications(db, current_user.id)


# ⚠️ STATIQUE en premier — avant /{notification_id}/mark-read
@router.post("/mark-read")
def mark_all_read(
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


# ⚠️ PARAMÈTRE après les statiques
@router.post("/{notification_id}/mark-read")
def mark_one_read(
    notification_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ok = notification_service.mark_one_read(db, notification_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}


# ════════════════════════════════════════
#  ADMIN NOTIFICATIONS
# ════════════════════════════════════════

@router.get("/admin", response_model=List[NotificationOut])
def admin_notifications(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return notification_service.get_admin_notifications(db)


# ⚠️ STATIQUE en premier — avant /admin/{notification_id}/mark-read
@router.post("/admin/mark-read")
def admin_mark_all_read(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    notification_service.mark_all_read_admin(db)
    db.commit()
    return {"ok": True}


@router.get("/admin/unread-count")
def admin_unread_count(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {"count": notification_service.unread_count_admin(db)}


# ⚠️ PARAMÈTRE après les statiques
@router.post("/admin/{notification_id}/mark-read")
def admin_mark_one_read(
    notification_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    ok = notification_service.mark_one_read_admin(db, notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}