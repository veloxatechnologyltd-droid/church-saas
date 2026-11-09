import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique, same_church_fk


class Event(ChurchScoped, Base):
    __tablename__ = "events"
    __table_args__ = (
        id_church_unique("events"),
        same_church_fk("events", "branch_id", "branches"),
        Index("ix_events_church_start", "church_id", "start_datetime"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    start_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_rule = Column(String, nullable=True)
    max_capacity = Column(Integer, nullable=True)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    registrations = relationship(
        "EventRegistration",
        back_populates="event",
        cascade="all, delete-orphan",
        foreign_keys="EventRegistration.event_id",
    )


class EventRegistration(ChurchScoped, Base):
    __tablename__ = "event_registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "member_id", name="uq_event_member"),
        same_church_fk("event_registrations", "event_id", "events", ondelete="CASCADE"),
        same_church_fk("event_registrations", "member_id", "members", ondelete="CASCADE"),
        Index("ix_event_registrations_church_id", "church_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    member_id = Column(UUID(as_uuid=True), nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event = relationship("Event", back_populates="registrations", foreign_keys=[event_id])
    member = relationship("Member", foreign_keys=[member_id])
