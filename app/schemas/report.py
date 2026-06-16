from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List


# ── Image ─────────────────────────────────────────────────────────

class ReportImageOut(BaseModel):
    id: int
    url: str
    model_config = {"from_attributes": True}


# ── Status History ────────────────────────────────────────────────

class StatusHistoryOut(BaseModel):
    id: int
    from_status: Optional[str]
    to_status: str
    changed_by: str
    changed_at: datetime
    model_config = {"from_attributes": True}


# ── Report ────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    title: str
    category: str
    wilaya: str
    commune: str
    description: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    priority: str = "normal"

    @field_validator("title", "commune", "description", "wilaya")
    @classmethod
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("This field cannot be empty")
        return v.strip()

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        allowed = {"road", "lighting", "waste", "water", "other"}
        if v not in allowed:
            raise ValueError(f"Category must be one of {allowed}")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in {"urgent", "normal", "low"}:
            return "normal"
        return v


class ReportStatusUpdate(BaseModel):
    status: str
    priority: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in {"pending", "processing", "resolved"}:
            raise ValueError("Invalid status")
        return v


class ReportOut(BaseModel):
    id: int
    ref_num: Optional[str]
    title: str
    category: str
    wilaya: str
    commune: str
    description: str
    status: str
    priority: str
    lat: Optional[float]
    lng: Optional[float]
    votes_count: int
    created_at: datetime
    updated_at: datetime
    user_id: int
    author_name: Optional[str] = None
    images: List[ReportImageOut] = []
    comments_count: Optional[int] = 0
    has_voted: Optional[bool] = False
    history: List[StatusHistoryOut] = []

    model_config = {"from_attributes": True}


class ReportListOut(BaseModel):
    id: int
    ref_num: Optional[str]
    title: str
    category: str
    wilaya: str
    commune: str
    status: str
    priority: str
    votes_count: int
    created_at: datetime
    author_name: Optional[str] = None
    images: List[ReportImageOut] = []
    comments_count: Optional[int] = 0
    has_voted: Optional[bool] = False

    model_config = {"from_attributes": True}


class PaginatedReports(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: List[ReportListOut]
