from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


# class UserRegister(BaseModel):
#     name: str
#     email: EmailStr
#     password: str
#     password_confirm: str

#     @field_validator("name")
#     @classmethod
#     def name_not_empty(cls, v):
#         if not v.strip():
#             raise ValueError("Name cannot be empty")
#         return v.strip()

#     @field_validator("password")
#     @classmethod
#     def password_min_length(cls, v):
#         if len(v) < 6:
#             raise ValueError("Password must be at least 6 characters")
#         return v

#     @field_validator("password_confirm")
#     @classmethod
#     def passwords_match(cls, v, info):
#         if "password" in info.data and v != info.data["password"]:
#             raise ValueError("Passwords do not match")
#         return v

from pydantic import BaseModel, EmailStr, field_validator, model_validator
from datetime import datetime
from typing import Optional


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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserProfile(UserOut):
    resolved_count: Optional[int] = 0


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
