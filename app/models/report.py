from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, func, Enum
)
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base


class ReportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    resolved = "resolved"


class ReportCategory(str, enum.Enum):
    road = "road"
    lighting = "lighting"
    waste = "waste"
    water = "water"
    other = "other"


class ReportPriority(str, enum.Enum):
    urgent = "urgent"
    normal = "normal"
    low = "low"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    ref_num = Column(String(30), unique=True, index=True)  # e.g. 2026/16/0001
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(500), nullable=False)
    category = Column(String(20), default="other", nullable=False)
    wilaya = Column(String(100), nullable=False)
    commune = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(String(20), default="pending", nullable=False)
    priority = Column(String(10), default="normal", nullable=False)

    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    votes_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("User", back_populates="reports")
    images = relationship("ReportImage", back_populates="report", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="report", cascade="all, delete-orphan", order_by="Comment.created_at")
    votes = relationship("Vote", back_populates="report", cascade="all, delete-orphan")
    history = relationship("StatusHistory", back_populates="report", cascade="all, delete-orphan", order_by="StatusHistory.changed_at")


class ReportImage(Base):
    __tablename__ = "report_images"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("Report", back_populates="images")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    changed_by = Column(String(50), default="admin")  # 'admin' or user id string
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("Report", back_populates="history")
