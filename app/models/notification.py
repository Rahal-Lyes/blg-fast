from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    # target: user_id (int) or NULL for admin
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    target_admin = Column(Boolean, default=False)  # True = destined to admin

    type = Column(String(30), nullable=False)       # new_report | new_user | status_update | vote | comment | report_sent
    title = Column(String(255), nullable=False)
    body = Column(String(500), nullable=False)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    target_user = relationship("User", back_populates="notifications")
