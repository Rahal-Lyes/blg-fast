from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError

from app.db.database import get_db
from app.schemas.user import UserRegister, UserLogin, AdminLogin, TokenResponse, LoginResponse, RefreshRequest
from app.models.user import User
from app.models.report import Report
from app.models.comment import Comment
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.services.notification_service import push_notif

router = APIRouter(prefix="/auth", tags=["Auth"])


def _user_payload(db: Session, user: User) -> dict:
    """Construit le dict utilisateur renvoyé au client."""
    reports_count  = db.query(func.count(Report.id)).filter(Report.user_id    == user.id).scalar() or 0
    comments_count = db.query(func.count(Comment.id)).filter(Comment.author_id == user.id).scalar() or 0
    return {
        "id":             user.id,
        "name":           user.name,
        "email":          user.email,
        "role":           user.role,
        "banned":         user.banned,
        "joined_at":      user.joined_at,
        "reports_count":  reports_count,
        "comments_count": comments_count,
    }


def _make_token_pair(user: User) -> tuple[str, str]:
    payload = {"sub": str(user.id), "role": user.role}
    return create_access_token(payload), create_refresh_token(payload)


@router.post("/register", response_model=LoginResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
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

    push_notif(db, type="new_user", title="مستخدم جديد",
               body=f"انضم {user.name} إلى المنصة", target_admin=True)
    db.commit()
    db.refresh(user)

    access, refresh = _make_token_pair(user)
    return {"access": access, "refresh": refresh, "user": _user_payload(db, user)}


@router.post("/login", response_model=LoginResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if user.banned:
        raise HTTPException(status_code=403, detail="This account has been suspended.")

    access, refresh = _make_token_pair(user)
    return {"access": access, "refresh": refresh, "user": _user_payload(db, user)}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Échange un refresh token valide contre un nouvel access token."""
    credentials_exc = HTTPException(status_code=401, detail="Refresh token invalide ou expiré.")
    try:
        data = decode_token(payload.refresh)
    except JWTError:
        raise credentials_exc

    if data.get("type") != "refresh":
        raise credentials_exc

    user_id = data.get("sub")
    role    = data.get("role")

    # Vérification que l'utilisateur existe toujours (et n'est pas banni)
    if role != "admin":
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or user.banned:
            raise credentials_exc

    new_access = create_access_token({"sub": user_id, "role": role})
    return {"access_token": new_access, "token_type": "bearer"}


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLogin):
    if payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect admin password.")
    token = create_access_token({"sub": "admin", "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}