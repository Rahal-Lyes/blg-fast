# routes/stats.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models import Report, User  

router = APIRouter()

@router.get("/stats")
def get_public_stats(db: Session = Depends(get_db)):
    
    # Total reports
    total = db.query(func.count(Report.id)).scalar()
    
    # Par statut
    pending    = db.query(func.count(Report.id)).filter(Report.status == "pending").scalar()
    processing = db.query(func.count(Report.id)).filter(Report.status == "processing").scalar()
    resolved   = db.query(func.count(Report.id)).filter(Report.status == "resolved").scalar()
    
    # Total users
    users = db.query(func.count(User.id)).scalar()

    return {
        "total":      total,
        "pending":    pending,
        "processing": processing,
        "resolved":   resolved,
        "users":      users,
    }