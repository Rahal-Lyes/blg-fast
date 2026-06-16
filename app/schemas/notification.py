from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: str
    report_id: Optional[int]
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
