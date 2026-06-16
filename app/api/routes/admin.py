import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app.db.database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.comment import Comment
from app.schemas.user import UserOut
from app.schemas.report import ReportOut, ReportListOut, PaginatedReports, ReportStatusUpdate
from app.schemas.comment import CommentOut
from app.core.security import require_admin
from app.services import report_service, notification_service

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dashboard Stats ───────────────────────────────────────────────
@router.get("/stats")
def dashboard_stats(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    total = db.query(func.count(Report.id)).scalar()
    pending = db.query(func.count(Report.id)).filter(Report.status == "pending").scalar()
    processing = db.query(func.count(Report.id)).filter(Report.status == "processing").scalar()
    resolved = db.query(func.count(Report.id)).filter(Report.status == "resolved").scalar()
    users_total = db.query(func.count(User.id)).scalar()
    resolution_rate = round((resolved / total * 100) if total else 0, 1)

    # Monthly counts (last 12 months)
    monthly = (
        db.query(
            extract("year", Report.created_at).label("year"),
            extract("month", Report.created_at).label("month"),
            func.count(Report.id).label("count"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .limit(12)
        .all()
    )

    # By category
    by_category = (
        db.query(Report.category, func.count(Report.id).label("count"))
        .group_by(Report.category)
        .all()
    )

    return {
        "total": total,
        "pending": pending,
        "processing": processing,
        "resolved": resolved,
        "users_total": users_total,
        "resolution_rate": resolution_rate,
        "monthly": [{"year": int(r.year), "month": int(r.month), "count": r.count} for r in monthly],
        "by_category": [{"category": r.category, "count": r.count} for r in by_category],
    }


# ── Reports Management ────────────────────────────────────────────
@router.get("/reports", response_model=PaginatedReports)
def admin_reports(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None,
    wilaya: Optional[str] = None,
    search: Optional[str] = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    total, items, pages = report_service.get_reports(
        db, page=page, per_page=per_page,
        status=status, category=category, wilaya=wilaya, search=search,
    )
    result = []
    for r in items:
        data = ReportListOut.model_validate(r)
        data.author_name = r.author.name if r.author else "—"
        data.comments_count = len(r.comments) if r.comments else 0
        result.append(data)
    return PaginatedReports(total=total, page=page, per_page=per_page, pages=pages, items=result)


@router.patch("/reports/{report_id}/status", response_model=ReportOut)
def update_status(
    report_id: int,
    payload: ReportStatusUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = report_service.update_status(
        db, report_id=report_id, new_status=payload.status, new_priority=payload.priority
    )
    status_labels = {"pending": "قيد الانتظار", "processing": "قيد المعالجة", "resolved": "تم الحل ✅"}
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


@router.delete("/reports/{report_id}")
def delete_report(
    report_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    report_service.delete_report(db, report_id)
    db.commit()
    return {"message": "Report deleted."}


# ── Admin Reply (official comment) ───────────────────────────────
@router.post("/reports/{report_id}/reply", response_model=CommentOut, status_code=201)
def admin_reply(
    report_id: int,
    body: dict,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Comment text is required.")
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


# ── Users Management ──────────────────────────────────────────────
@router.get("/users")
def list_users(
    search: Optional[str] = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if search:
        q = q.filter(
            User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )
    users = q.order_by(User.joined_at.desc()).all()
    result = []
    for u in users:
        rc = db.query(func.count(Report.id)).filter(Report.user_id == u.id).scalar()
        data = UserOut.model_validate(u)
        data.reports_count = rc
        result.append(data)
    return result


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
    return {"message": "User deleted."}


# ── Delete Comment ────────────────────────────────────────────────
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
    return {"message": "Comment deleted."}


# ── CSV Export ────────────────────────────────────────────────────
@router.get("/export/csv")
def export_csv(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Ref", "Title", "Category", "Wilaya", "Commune",
                     "Status", "Priority", "Votes", "Date", "Description"])
    for r in reports:
        writer.writerow([
            r.id, r.ref_num or "", r.title, r.category, r.wilaya,
            r.commune, r.status, r.priority, r.votes_count,
            r.created_at.strftime("%Y-%m-%d"), r.description,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=balligh_reports.csv"},
    )
