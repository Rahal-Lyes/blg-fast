# app/api/routes/stats.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models import Report, User

router = APIRouter(prefix="/stats")

VALID_STATUSES   = {"pending", "processing", "resolved"}
VALID_CATEGORIES = {"road", "lighting", "waste", "water", "other"}
VALID_PRIORITIES = {"urgent", "normal", "low"}

@router.get("/")
def get_public_stats(db: Session = Depends(get_db)):

    # ── Totaux par statut ─────────────────────────────────────────
    status_rows = (
        db.query(Report.status, func.count(Report.id))
        .group_by(Report.status)
        .all()
    )
    by_status = {s: 0 for s in VALID_STATUSES}
    for status, count in status_rows:
        if status in VALID_STATUSES:
            by_status[status] = count

    # ── Totaux par catégorie ──────────────────────────────────────
    cat_rows = (
        db.query(Report.category, func.count(Report.id))
        .group_by(Report.category)
        .all()
    )
    by_category = {c: 0 for c in VALID_CATEGORIES}
    for category, count in cat_rows:
        if category in VALID_CATEGORIES:
            by_category[category] = count

    # ── Totaux par priorité ───────────────────────────────────────
    prio_rows = (
        db.query(Report.priority, func.count(Report.id))
        .group_by(Report.priority)
        .all()
    )
    by_priority = {p: 0 for p in VALID_PRIORITIES}
    for priority, count in prio_rows:
        if priority in VALID_PRIORITIES:
            by_priority[priority] = count

    # ── Total global ──────────────────────────────────────────────
    total   = sum(by_status.values())
    users   = db.query(func.count(User.id)).scalar()

    return {
        "total":       total,
        "users":       users,
        "by_status":   by_status,
        "by_category": by_category,
        "by_priority": by_priority,
    }