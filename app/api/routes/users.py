from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.comment import Comment
from app.schemas.user import UserProfile, ChangePassword
from app.core.security import require_auth, verify_password, hash_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfile)
def get_profile(current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    reports_count = db.query(func.count(Report.id)).filter(Report.user_id == current_user.id).scalar()
    resolved_count = db.query(func.count(Report.id)).filter(
        Report.user_id == current_user.id, Report.status == "resolved"
    ).scalar()
    comments_count = db.query(func.count(Comment.id)).filter(Comment.author_id == current_user.id).scalar()

    result = UserProfile.model_validate(current_user)
    result.reports_count = reports_count
    result.resolved_count = resolved_count
    result.comments_count = comments_count
    return result


@router.patch("/me/password")
def change_password(
    payload: ChangePassword,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}
