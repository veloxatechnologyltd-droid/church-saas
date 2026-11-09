import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.models.tenant import ChurchScoped, same_church_fk


class Announcement(ChurchScoped, Base):
    __tablename__ = "announcements"
    __table_args__ = (
        same_church_fk("announcements", "branch_id", "branches"),
        Index("ix_announcements_church_active_publish", "church_id", "is_active", "publish_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, server_default=text("true"), nullable=False, index=True)
    publish_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
