import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, same_church_fk


class PastoralLog(ChurchScoped, Base):
    __tablename__ = "pastoral_logs"
    __table_args__ = (
        same_church_fk("pastoral_logs", "member_id", "members", ondelete="CASCADE"),
        same_church_fk("pastoral_logs", "branch_id", "branches"),
        Index("ix_pastoral_logs_church_status_due", "church_id", "status", "follow_up_date"),
        Index("ix_pastoral_logs_church_member", "church_id", "member_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    log_type = Column(String, nullable=False)
    notes = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="open", index=True)
    priority = Column(String, nullable=False, default="normal")
    source = Column(String, nullable=False, default="manual")
    follow_up_date = Column(Date, nullable=True, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    logged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    log_date = Column(Date, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    member = relationship("Member", foreign_keys=[member_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    logger = relationship("User", foreign_keys=[logged_by])
