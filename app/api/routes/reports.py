from typing import Optional, List
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.schemas.report import ReportOut, ReportListOut, PaginatedReports
from app.schemas.comment import CommentCreate, CommentOut
from app.models.user import User
from app.models.comment import Comment
from app.models.report import Report
from app.core.security import get_current_user, require_auth
from app.services import report_service, notification_service

router = APIRouter(prefix="/reports", tags=["Reports"])


# ── List / Search ─────────────────────────────────────────────────
@router.get("", response_model=PaginatedReports)
def list_reports(
    page: int = 1,
    per_page: int = 12,
    status: Optional[str] = None,
    category: Optional[str] = None,
    wilaya: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
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
        if current_user:
            data.has_voted = report_service.user_has_voted(db, r.id, current_user.id)
        result.append(data)

    return PaginatedReports(total=total, page=page, per_page=per_page, pages=pages, items=result)


# ── Map (all geo-tagged reports) ──────────────────────────────────
@router.get("/map", response_model=List[ReportListOut])
def map_reports(db: Session = Depends(get_db)):
    from app.models.report import Report
    from sqlalchemy.orm import joinedload
    items = (
        db.query(Report)
        .options(joinedload(Report.author), joinedload(Report.images))
        .filter(Report.lat.isnot(None), Report.lng.isnot(None))
        .all()
    )
    result = []
    for r in items:
        data = ReportListOut.model_validate(r)
        data.author_name = r.author.name if r.author else "—"
        result.append(data)
    return result


# ── My Reports ────────────────────────────────────────────────────
@router.get("/mine", response_model=PaginatedReports)
def my_reports(
    page: int = 1,
    per_page: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    total, items, pages = report_service.get_reports(
        db, page=page, per_page=per_page, user_id=current_user.id
    )
    result = []
    for r in items:
        data = ReportListOut.model_validate(r)
        data.author_name = current_user.name
        data.comments_count = len(r.comments) if r.comments else 0
        data.has_voted = True
        result.append(data)
    return PaginatedReports(total=total, page=page, per_page=per_page, pages=pages, items=result)


# ── Create Report ─────────────────────────────────────────────────
# @router.post("", response_model=ReportOut, status_code=201)
# def create_report(
#     title: str = Form(...),
#     category: str = Form(...),
#     wilaya: str = Form(...),
#     commune: str = Form(...),
#     description: str = Form(...),
#     lat: Optional[float] = Form(None),
#     lng: Optional[float] = Form(None),
#     priority: str = Form("normal"),
#     images: List[UploadFile] = File(default=[]),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_auth),
# ):
#     report = report_service.create_report(
#         db,
#         user_id=current_user.id,
#         title=title,
#         category=category,
#         wilaya=wilaya,
#         commune=commune,
#         description=description,
#         lat=lat,
#         lng=lng,
#         priority=priority,
#         images=[img for img in images if img.filename],
#     )
#     # Notifications
#     notification_service.push_notif(
#         db, type="new_report", title="📋 بلاغ جديد",
#         body=f"المواطن {current_user.name} أرسل: {title}",
#         report_id=report.id, target_admin=True,
#     )
#     notification_service.push_notif(
#         db, type="report_sent", title="تم إرسال بلاغك بنجاح!",
#         body=title, report_id=report.id, target_user_id=current_user.id,
#     )
#     db.commit()
#     db.refresh(report)

#     out = ReportOut.model_validate(report)
#     out.author_name = current_user.name
#     out.user_id = current_user.id
#     return out

# ── Dans routes/reports.py — remplace uniquement create_report ────

@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    title: str = Form(...),
    category: str = Form(...),
    wilaya: str = Form(...),
    wilaya_id: Optional[str] = Form(None),   # ← NOUVEAU
    commune: str = Form(...),
    description: str = Form(...),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    priority: str = Form("normal"),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    report = report_service.create_report(
        db,
        user_id=current_user.id,
        title=title,
        category=category,
        wilaya=wilaya,
        wilaya_id=wilaya_id,               # ← NOUVEAU
        commune=commune,
        description=description,
        lat=lat,
        lng=lng,
        priority=priority,
        images=[img for img in images if img.filename],
    )
    notification_service.push_notif(
        db, type="new_report", title="📋 بلاغ جديد",
        body=f"المواطن {current_user.name} أرسل: {title}",
        report_id=report.id, target_admin=True,
    )
    notification_service.push_notif(
        db, type="report_sent", title="تم إرسال بلاغك بنجاح!",
        body=title, report_id=report.id, target_user_id=current_user.id,
    )
    db.commit()
    db.refresh(report)

    out = ReportOut.model_validate(report)
    out.author_name = current_user.name
    out.user_id = current_user.id
    return out



# ── Get Detail ────────────────────────────────────────────────────
@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    report = report_service.get_report_detail(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    out = ReportOut.model_validate(report)
    out.author_name = report.author.name if report.author else "—"
    out.comments_count = len(report.comments)
    if current_user:
        out.has_voted = report_service.user_has_voted(db, report_id, current_user.id)
    return out


# ── Vote ──────────────────────────────────────────────────────────
@router.post("/{report_id}/vote")
def vote(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    already_voted, new_count = report_service.toggle_vote(db, report_id=report_id, user_id=current_user.id)
    if not already_voted:
        report = db.query(Report).filter(Report.id == report_id).first()
        notification_service.push_notif(
            db, type="vote", title="👍 تصويت جديد",
            body=f"{report.title} ({new_count})",
            report_id=report_id,
            target_user_id=report.user_id,
        )
    db.commit()
    return {"votes_count": new_count, "already_voted": already_voted}


# ── Add Comment ───────────────────────────────────────────────────
@router.post("/{report_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    report_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    comment = Comment(
        report_id=report_id,
        author_id=current_user.id,
        author_name=current_user.name,
        is_admin=False,
        text=payload.text.strip(),
    )
    db.add(comment)
    db.flush()
    notification_service.push_notif(
        db, type="comment", title="💬 تعليق جديد",
        body=f"{current_user.name}: {report.title}",
        report_id=report_id, target_admin=True,
    )
    db.commit()
    db.refresh(comment)
    return comment
