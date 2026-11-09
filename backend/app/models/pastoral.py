import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class PastoralLog(Base):
    __tablename__ = "pastoral_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    log_type = Column(String, nullable=False)
    notes = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="open", index=True)
    priority = Column(String, nullable=False, default="normal")
    source = Column(String, nullable=False, default="manual")
    follow_up_date = Column(Date, nullable=True, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    logged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    log_date = Column(Date, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    member = relationship("Member")
    assignee = relationship("User", foreign_keys=[assigned_to])
    logger = relationship("User", foreign_keys=[logged_by])
