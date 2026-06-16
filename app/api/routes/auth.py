from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.schemas.user import UserRegister, UserLogin, AdminLogin, TokenResponse, LoginResponse
from app.models.user import User
from app.models.report import Report
from app.models.comment import Comment
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.services.notification_service import push_notif

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=LoginResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    # Check email uniqueness
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="This email is already in use.")

    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role="citizen",
    )
    db.add(user)
    db.flush()

    # Notify admin
    push_notif(
        db,
        type="new_user",
        title="مستخدم جديد",
        body=f"انضم {user.name} إلى المنصة",
        target_admin=True,
    )
    db.commit()
    db.refresh(user)

    # Get counts
    reports_count = db.query(func.count(Report.id)).filter(Report.user_id == user.id).scalar() or 0
    comments_count = db.query(func.count(Comment.id)).filter(Comment.author_id == user.id).scalar() or 0

    token = create_access_token({"sub": str(user.id), "role": "citizen"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "banned": user.banned,
            "joined_at": user.joined_at,
            "reports_count": reports_count,
            "comments_count": comments_count,
        }
    }


@router.post("/login", response_model=LoginResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if user.banned:
        raise HTTPException(status_code=403, detail="This account has been suspended.")

    # Get counts
    reports_count = db.query(func.count(Report.id)).filter(Report.user_id == user.id).scalar() or 0
    comments_count = db.query(func.count(Comment.id)).filter(Comment.author_id == user.id).scalar() or 0

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "banned": user.banned,
            "joined_at": user.joined_at,
            "reports_count": reports_count,
            "comments_count": comments_count,
        }
    }


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLogin):
    if payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect admin password.")
    token = create_access_token({"sub": "admin", "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}
