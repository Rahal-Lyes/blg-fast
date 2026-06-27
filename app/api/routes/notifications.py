from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.notification import NotificationOut
from app.core.security import require_auth, require_admin
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ════════════════════════════════════════════════════════
#  ADMIN — toutes les routes /admin/* EN PREMIER
#  (avant les routes /{notification_id} qui les avaleraient)
# ════════════════════════════════════════════════════════

@router.get("/admin", response_model=List[NotificationOut])
def admin_get_notifications(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return notification_service.get_admin_notifications(db)


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


# ════════════════════════════════════════════════════════
#  USER — routes statiques avant /{notification_id}
# ════════════════════════════════════════════════════════

@router.get("", response_model=List[NotificationOut])
def user_get_notifications(
    current_user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    return notification_service.get_user_notifications(db, current_user.id)


@router.post("/mark-read")
def user_mark_all_read(
    current_user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    notification_service.mark_all_read_user(db, current_user.id)
    db.commit()
    return {"ok": True}


@router.get("/unread-count")
def user_unread_count(
    current_user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    return {"count": notification_service.unread_count_user(db, current_user.id)}


@router.post("/{notification_id}/mark-read")
def user_mark_one_read(
    notification_id: int,
    current_user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    ok = notification_service.mark_one_read(db, notification_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}