from sqlalchemy.orm import Session
from app.models.notification import Notification


def push_notif(
    db: Session,
    *,
    type: str,
    title: str,
    body: str,
    report_id: int = None,
    target_user_id: int = None,
    target_admin: bool = False,
):
    notif = Notification(
        type=type,
        title=title,
        body=body,
        report_id=report_id,
        target_user_id=target_user_id,
        target_admin=target_admin,
    )
    db.add(notif)
    db.flush()
    return notif


def get_user_notifications(db: Session, user_id: int, limit: int = 50):
    return (
        db.query(Notification)
        .filter(Notification.target_user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def get_admin_notifications(db: Session, limit: int = 50):
    return (
        db.query(Notification)
        .filter(Notification.target_admin == True)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_all_read_user(db: Session, user_id: int):
    db.query(Notification).filter(
        Notification.target_user_id == user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.flush()


def mark_all_read_admin(db: Session):
    db.query(Notification).filter(
        Notification.target_admin == True,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.flush()


def unread_count_user(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(Notification.target_user_id == user_id, Notification.is_read == False)
        .count()
    )


def unread_count_admin(db: Session) -> int:
    return (
        db.query(Notification)
        .filter(Notification.target_admin == True, Notification.is_read == False)
        .count()
    )
