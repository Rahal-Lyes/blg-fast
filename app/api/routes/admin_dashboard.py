"""
app/api/routes/admin_dashboard.py
──────────────────────────────────
Single "fat" endpoint that returns everything AdminView needs in one request,
avoiding the N+1 waterfall of separate /admin/stats, /admin/reports, /admin/users calls.

Mount in main.py:
    from app.api.routes import admin_dashboard
    app.include_router(admin_dashboard.router)
"""

import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, case, and_

from app.db.database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.comment import Comment
from app.schemas.user import UserOut
from app.schemas.report import ReportOut, ReportListOut, ReportStatusUpdate
from app.schemas.comment import CommentOut
from app.core.security import require_admin
from app.services import report_service, notification_service

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /admin/dashboard  ← the ONE endpoint AdminView calls on mount
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/dashboard")
def get_dashboard(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Returns everything the AdminView needs in a single round-trip:
      • stats        – KPI counters
      • monthly      – bar chart data (last 12 months, keyed "YYYY-MM")
      • weekly       – line chart data (last 8 weeks, keyed "Wxx")
      • by_category  – doughnut chart data
      • by_wilaya    – horizontal bar (top 10 wilayas)
      • avg_resolution_days – time-to-resolve KPI
      • reports      – full paginated list (latest 200 for client-side filter)
      • users        – full user list with per-user report counts
    """

    # ── KPI counters ──────────────────────────────────────────────
    total       = db.query(func.count(Report.id)).scalar() or 0
    pending     = db.query(func.count(Report.id)).filter(Report.status == "pending").scalar() or 0
    processing  = db.query(func.count(Report.id)).filter(Report.status == "processing").scalar() or 0
    resolved    = db.query(func.count(Report.id)).filter(Report.status == "resolved").scalar() or 0
    users_total = db.query(func.count(User.id)).scalar() or 0
    rate        = round((resolved / total * 100) if total else 0, 1)

    # ── Average resolution time (days) ────────────────────────────
    # Requires a resolved_at column; fall back to created_at diff if missing.
    try:
        avg_days_row = (
            db.query(func.avg(
                func.julianday(Report.resolved_at) - func.julianday(Report.created_at)
            ))
            .filter(Report.status == "resolved", Report.resolved_at.isnot(None))
            .scalar()
        )
        avg_resolution_days = round(float(avg_days_row), 1) if avg_days_row else None
    except Exception:
        avg_resolution_days = None

    # ── Monthly counts (last 12 months) ───────────────────────────
    rows = (
        db.query(
            extract("year",  Report.created_at).label("y"),
            extract("month", Report.created_at).label("m"),
            func.count(Report.id).label("cnt"),
        )
        .group_by("y", "m")
        .order_by("y", "m")
        .all()
    )
    monthly = {}
    for r in rows:
        key = f"{int(r.y)}-{int(r.m):02d}"
        monthly[key] = r.cnt
    # Keep last 12 entries only
    monthly = dict(list(monthly.items())[-12:])

    # ── Weekly counts (last 8 weeks) ──────────────────────────────
    eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)
    weekly_rows = (
        db.query(
            extract("year", Report.created_at).label("y"),
            extract("week", Report.created_at).label("w"),
            func.count(Report.id).label("cnt"),
        )
        .filter(Report.created_at >= eight_weeks_ago)
        .group_by("y", "w")
        .order_by("y", "w")
        .all()
    )
    weekly = {f"S{int(r.w):02d}": r.cnt for r in weekly_rows}

    # ── By category ───────────────────────────────────────────────
    cat_rows = (
        db.query(Report.category, func.count(Report.id).label("cnt"))
        .group_by(Report.category)
        .all()
    )
    by_category = {r.category: r.cnt for r in cat_rows}

    # ── By wilaya (top 10) ────────────────────────────────────────
    wilaya_rows = (
        db.query(Report.wilaya, func.count(Report.id).label("cnt"))
        .filter(Report.wilaya.isnot(None))
        .group_by(Report.wilaya)
        .order_by(func.count(Report.id).desc())
        .limit(10)
        .all()
    )
    by_wilaya = {r.wilaya: r.cnt for r in wilaya_rows}

    # ── Status over time (stacked for area chart) ─────────────────
    status_monthly_rows = (
        db.query(
            extract("year",  Report.created_at).label("y"),
            extract("month", Report.created_at).label("m"),
            Report.status,
            func.count(Report.id).label("cnt"),
        )
        .group_by("y", "m", Report.status)
        .order_by("y", "m")
        .all()
    )
    status_monthly: dict = defaultdict(lambda: {"pending": 0, "processing": 0, "resolved": 0})
    for r in status_monthly_rows:
        key = f"{int(r.y)}-{int(r.m):02d}"
        status_monthly[key][r.status] = r.cnt
    status_monthly = dict(list(status_monthly.items())[-12:])

    # ── Reports (latest 200, client handles search/filter) ────────
    reports_q = (
        db.query(Report)
        .options(joinedload(Report.author), joinedload(Report.images))
        .order_by(Report.created_at.desc())
        .limit(200)
        .all()
    )
    reports_out = []
    for r in reports_q:
        d = ReportListOut.model_validate(r)
        d.author_name   = r.author.name if r.author else "—"
        d.comments_count = len(r.comments) if hasattr(r, "comments") and r.comments else 0
        reports_out.append(d.model_dump())

    # ── Users (with per-user report count inline) ─────────────────
    # Single query: user + count via subquery avoids N+1
    report_counts = dict(
        db.query(Report.user_id, func.count(Report.id))
        .group_by(Report.user_id)
        .all()
    )
    users_q = db.query(User).order_by(User.joined_at.desc()).all()
    users_out = []
    for u in users_q:
        d = UserOut.model_validate(u)
        data = d.model_dump()
        data["reports_count"] = report_counts.get(u.id, 0)
        users_out.append(data)

    return {
        "stats": {
            "total":               total,
            "pending":             pending,
            "processing":          processing,
            "resolved":            resolved,
            "users":               users_total,
            "rate":                rate,
            "avg_resolution_days": avg_resolution_days,
        },
        "monthly":        monthly,
        "weekly":         weekly,
        "by_category":    by_category,
        "by_wilaya":      by_wilaya,
        "status_monthly": status_monthly,
        "reports":        reports_out,
        "users":          users_out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /admin/reports/{id}/status
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/reports/{report_id}/status", response_model=ReportOut)
def update_status(
    report_id: int,
    payload: ReportStatusUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = report_service.update_status(
        db, report_id=report_id,
        new_status=payload.status,
        new_priority=payload.priority,
    )
    status_labels = {
        "pending":    "قيد الانتظار",
        "processing": "قيد المعالجة",
        "resolved":   "تم الحل ✅",
    }
    notification_service.push_notif(
        db, type="status_update", title="🔄 تحديث الحالة",
        body=f"{report.title}: {status_labels.get(payload.status, payload.status)}",
        report_id=report_id, target_user_id=report.user_id,
    )
    db.commit()
    db.refresh(report)
    out = ReportOut.model_validate(report)
    out.author_name = report.author.name if report.author else "—"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /admin/reports/{id}
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/reports/{report_id}")
def delete_report(
    report_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    report_service.delete_report(db, report_id)
    db.commit()
    return {"ok": True, "id": report_id}


# ─────────────────────────────────────────────────────────────────────────────
# POST /admin/reports/{id}/reply
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/reports/{report_id}/reply", response_model=CommentOut, status_code=201)
def admin_reply(
    report_id: int,
    body: dict,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Comment text required.")
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    comment = Comment(
        report_id=report_id,
        author_id=None,
        author_name="المسؤول 🛡️",
        is_admin=True,
        text=text,
    )
    db.add(comment)
    db.flush()
    notification_service.push_notif(
        db, type="comment", title="💬 رد رسمي",
        body=report.title, report_id=report_id, target_user_id=report.user_id,
    )
    db.commit()
    db.refresh(comment)
    return comment


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /admin/users/{id}/ban   |   DELETE /admin/users/{id}
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/users/{user_id}/ban")
def toggle_ban(
    user_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.banned = not user.banned
    db.commit()
    return {"id": user.id, "banned": user.banned}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"ok": True, "id": user_id}


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /admin/comments/{id}
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(comment)
    db.commit()
    return {"ok": True, "id": comment_id}


# ─────────────────────────────────────────────────────────────────────────────
# GET /admin/export/csv
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/export/csv")
def export_csv(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    output  = io.StringIO()
    writer  = csv.writer(output)
    writer.writerow([
        "ID", "Ref", "Title", "Category", "Wilaya", "Commune",
        "Status", "Priority", "Votes", "Date", "Description",
    ])
    for r in reports:
        writer.writerow([
            r.id, r.ref_num or "", r.title, r.category,
            r.wilaya, r.commune, r.status, r.priority,
            r.votes_count, r.created_at.strftime("%Y-%m-%d"), r.description,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=balligh_reports.csv"},
    )