import os
import uuid
import math
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from fastapi import UploadFile, HTTPException

from app.models.report import Report, ReportImage, StatusHistory
from app.models.vote import Vote
from app.models.user import User
from app.models.comment import Comment
from app.core.config import settings


# ── Wilaya codes (generated from wilayas.json — all 69 wilayas) ───
WILAYA_CODES: dict[str, str] = {
    "أدرار": "01",       # Adrar
    "الشلف": "02",       # Chlef
    "الأغواط": "03",     # Laghouat
    "أم البواقي": "04",  # Oum El Bouaghi
    "باتنة": "05",       # Batna
    "بجاية": "06",       # Béjaïa
    "بسكرة": "07",       # Biskra
    "بشار": "08",        # Bechar
    "البليدة": "09",     # Blida
    "البويرة": "10",     # Bouira
    "تمنراست": "11",     # Tamanrasset
    "تبسة": "12",        # Tbessa
    "تلمسان": "13",      # Tlemcen
    "تيارت": "14",       # Tiaret
    "تيزي وزو": "15",    # Tizi Ouzou
    "الجزائر": "16",     # Alger
    "الجلفة": "17",      # Djelfa
    "جيجل": "18",        # Jijel
    "سطيف": "19",        # Setif
    "سعيدة": "20",       # Saida
    "سكيكدة": "21",      # Skikda
    "سيدي بلعباس": "22", # Sidi Bel Abbes
    "عنابة": "23",       # Annaba
    "قالمة": "24",       # Guelma
    "قسنطينة": "25",     # Constantine
    "المدية": "26",      # Medea
    "مستغانم": "27",     # Mostaganem
    "المسيلة": "28",     # M'Sila
    "معسكر": "29",       # Mascara
    "ورقلة": "30",       # Ouargla
    "وهران": "31",       # Oran
    "البيض": "32",       # El Bayadh
    "إليزي": "33",       # Illizi
    "برج بوعريريج": "34",# Bordj Bou Arreridj
    "بومرداس": "35",     # Boumerdes
    "الطارف": "36",      # El Tarf
    "تندوف": "37",       # Tindouf
    "تيسمسيلت": "38",    # Tissemsilt
    "الوادي": "39",      # El Oued
    "خنشلة": "40",       # Khenchela
    "سوق أهراس": "41",   # Souk Ahras
    "تيبازة": "42",      # Tipaza
    "ميلة": "43",        # Mila
    "عين الدفلى": "44",  # Ain Defla
    "النعامة": "45",     # Naama
    "عين تموشنت": "46",  # Ain Temouchent
    "غرداية": "47",      # Ghardaia
    "غليزان": "48",      # Relizane
    "المغير": "49",      # El M'ghair
    "المنيعة": "50",     # El Menia
    "أولاد جلال": "51",  # Ouled Djellal
    "برج باجي مختار": "52", # Bordj Baji Mokhtar
    "بني عباس": "53",    # Béni Abbès
    "تيميمون": "54",     # Timimoun
    "تقرت": "55",        # Touggourt
    "جانت": "56",        # Djanet
    "عين صالح": "57",    # In Salah
    "عين قزام": "58",    # In Guezzam
    "آفلو": "59",        # Aflou
    "بريكة": "60",       # Barika
    "القنطرة": "61",     # El Kantara
    "بئر العاتر": "62",  # Bir El Ater
    "العريشة": "63",     # El Aricha
    "قصر الشلالة": "64", # Ksar Chellala
    "عين وسارة": "65",   # Ain Oussera
    "مسعد": "66",        # Messad
    "قصر البخاري": "67", # Ksar El Boukhari
    "بوسعادة": "68",     # Bou Saada
    "الأبيض سيدي الشيخ": "69", # El Abiodh Sidi Cheikh
}


# ── ref_num generation ─────────────────────────────────────────────
def generate_ref_num(db: Session, wilaya: str, wilaya_id: Optional[str] = None) -> str:
    """
    Format: YYYY/WW/NNNN
      YYYY : current year
      WW   : wilaya code (2 digits)
      NNNN : collision-safe sequence for this wilaya+year
    """
    year = datetime.now().year

    # wilaya_id (from JSON "id" field) takes priority
    if wilaya_id and wilaya_id.strip():
        code = str(wilaya_id).strip().zfill(2)
    else:
        code = WILAYA_CODES.get(wilaya, "00")

    prefix = f"{year}/{code}/"

    existing_count = (
        db.query(func.count(Report.id))
        .filter(Report.ref_num.like(f"{prefix}%"))
        .scalar()
    ) or 0

    for attempt in range(500):
        candidate = f"{prefix}{str(existing_count + 1 + attempt).zfill(4)}"
        taken = (
            db.query(func.count(Report.id))
            .filter(Report.ref_num == candidate)
            .scalar()
        ) > 0
        if not taken:
            return candidate

    return f"{prefix}{str(existing_count + 1).zfill(4)}-{uuid.uuid4().hex[:6]}"


# ── Image saving ───────────────────────────────────────────────────
def save_image(upload: UploadFile) -> tuple[str, str]:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(upload.filename or "")[-1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=400, detail=f"Invalid image type: {ext}")
    filename = f"img_{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return filename, f"/uploads/{filename}"


# ── Create report ──────────────────────────────────────────────────
def create_report(
    db: Session,
    *,
    user_id: int,
    title: str,
    category: str,
    wilaya: str,
    wilaya_id: Optional[str] = None,
    commune: str,
    description: str,
    lat: Optional[float],
    lng: Optional[float],
    priority: str = "normal",
    images: List[UploadFile] = [],
) -> Report:
    ref_num = generate_ref_num(db, wilaya, wilaya_id)

    report = Report(
        user_id=user_id,
        ref_num=ref_num,
        title=title,
        category=category,
        wilaya=wilaya,
        commune=commune,
        description=description,
        lat=lat,
        lng=lng,
        priority=priority,
        status="pending",
    )
    db.add(report)
    db.flush()

    for upload in images[: settings.MAX_IMAGES_PER_REPORT]:
        if upload.filename:
            filename, url = save_image(upload)
            db.add(ReportImage(report_id=report.id, filename=filename, url=url))

    db.add(StatusHistory(
        report_id=report.id,
        from_status=None,
        to_status="pending",
        changed_by=str(user_id),
    ))
    db.flush()
    return report


# ── List / search ──────────────────────────────────────────────────
def get_reports(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 12,
    status: Optional[str] = None,
    category: Optional[str] = None,
    wilaya: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[int] = None,
):
    q = db.query(Report).options(
        joinedload(Report.images),
        joinedload(Report.author),
    )
    if status:
        q = q.filter(Report.status == status)
    if category:
        q = q.filter(Report.category == category)
    if wilaya:
        q = q.filter(Report.wilaya == wilaya)
    if search:
        q = q.filter(or_(
            Report.title.ilike(f"%{search}%"),
            Report.description.ilike(f"%{search}%"),
            Report.commune.ilike(f"%{search}%"),
        ))
    if user_id:
        q = q.filter(Report.user_id == user_id)

    total = q.count()
    items = (
        q.order_by(Report.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return total, items, math.ceil(total / per_page) if total else 1


# ── Detail ─────────────────────────────────────────────────────────
def get_report_detail(db: Session, report_id: int) -> Optional[Report]:
    return (
        db.query(Report)
        .options(
            joinedload(Report.images),
            joinedload(Report.author),
            joinedload(Report.comments),
            joinedload(Report.history),
        )
        .filter(Report.id == report_id)
        .first()
    )


# ── Update status ──────────────────────────────────────────────────
def update_status(
    db: Session,
    *,
    report_id: int,
    new_status: str,
    new_priority: Optional[str] = None,
) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != new_status:
        db.add(StatusHistory(
            report_id=report_id,
            from_status=report.status,
            to_status=new_status,
            changed_by="admin",
        ))
        report.status = new_status
    if new_priority and new_priority in {"urgent", "normal", "low"}:
        report.priority = new_priority
    db.flush()
    return report


# ── Vote ───────────────────────────────────────────────────────────
def toggle_vote(db: Session, *, report_id: int, user_id: int) -> tuple[bool, int]:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    existing = db.query(Vote).filter(
        Vote.report_id == report_id, Vote.user_id == user_id
    ).first()
    if existing:
        return True, report.votes_count
    db.add(Vote(report_id=report_id, user_id=user_id))
    report.votes_count += 1
    db.flush()
    return False, report.votes_count


def user_has_voted(db: Session, report_id: int, user_id: int) -> bool:
    return db.query(Vote).filter(
        Vote.report_id == report_id, Vote.user_id == user_id
    ).first() is not None


# ── Delete ─────────────────────────────────────────────────────────
def delete_report(db: Session, report_id: int):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    for img in report.images:
        path = os.path.join(settings.UPLOAD_DIR, img.filename)
        if os.path.exists(path):
            os.remove(path)
    db.delete(report)
    db.flush()