from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CommentCreate(BaseModel):
    text: str
    report_id: int


class CommentOut(BaseModel):
    id: int
    report_id: int
    author_id: Optional[int]
    author_name: str
    is_admin: bool
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}
