from pydantic import BaseModel, EmailStr, field_validator, model_validator
from datetime import datetime
from typing import Optional


# ─── Entrées ────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AdminLogin(BaseModel):
    password: str


class RefreshRequest(BaseModel):
    refresh: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str
    new_password_confirm: str

    @field_validator("new_password")
    @classmethod
    def min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("new_password_confirm")
    @classmethod
    def match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# ─── Sorties ─────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    banned: bool
    joined_at: datetime
    reports_count: Optional[int] = 0
    comments_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class UserProfile(UserOut):
    resolved_count: Optional[int] = 0


class TokenResponse(BaseModel):
    """Réponse admin : access token seul, sans refresh."""
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Réponse login/register citoyen : paire de tokens + profil."""
    access: str           # ← correspond à la clé lue par AuthStore._setTokens()
    refresh: str          # ← idem
    token_type: str = "bearer"
    user: UserOut


class RefreshResponse(BaseModel):
    """Réponse de /auth/refresh : nouvel access token."""
    access_token: str
    token_type: str = "bearer"