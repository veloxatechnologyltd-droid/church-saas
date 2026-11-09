import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique, same_church_fk


class Communication(ChurchScoped, Base):
    __tablename__ = "communications"
    __table_args__ = (
        id_church_unique("communications"),
        same_church_fk("communications", "group_id", "groups"),
        Index("ix_communications_church_sent", "church_id", "sent_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False, default="sms")
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    audience_type = Column(String, nullable=True)
    group_id = Column(UUID(as_uuid=True), nullable=True)
    recipients = Column(Text, nullable=True)  # JSON array of recipient member IDs
    recipient_count = Column(Integer, default=0, nullable=False)
    successful_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    provider_message_id = Column(String, nullable=True)
    credits_used = Column(Integer, nullable=True)
    sent_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    status = Column(String, nullable=False, default="queued")

    group = relationship("Group", foreign_keys=[group_id])


class ReminderSchedule(ChurchScoped, Base):
    """A recurring weekly message definition, evaluated by the reminder runner."""

    __tablename__ = "reminder_schedules"
    __table_args__ = (
        id_church_unique("reminder_schedules"),
        same_church_fk("reminder_schedules", "group_id", "groups"),
        Index("ix_reminder_schedules_church_active", "church_id", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    message_template = Column(Text, nullable=False)
    frequency = Column(String, nullable=False, default="weekly")
    weekday = Column(Integer, nullable=False)  # Python weekday: Monday=0 ... Sunday=6
    send_time = Column(Time, nullable=False)
    timezone = Column(String, nullable=False, default="Africa/Accra")
    audience_type = Column(String, nullable=False, default="all_members")
    group_id = Column(UUID(as_uuid=True), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    group = relationship("Group", foreign_keys=[group_id])


class ReminderRun(ChurchScoped, Base):
    __tablename__ = "reminder_runs"
    __table_args__ = (
        UniqueConstraint("schedule_id", "scheduled_for", name="uq_reminder_schedule_run"),
        same_church_fk("reminder_runs", "schedule_id", "reminder_schedules", ondelete="CASCADE"),
        same_church_fk("reminder_runs", "communication_id", "communications"),
        Index("ix_reminder_runs_church_id", "church_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(UUID(as_uuid=True), nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    communication_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    schedule = relationship("ReminderSchedule", foreign_keys=[schedule_id])
    communication = relationship("Communication", foreign_keys=[communication_id])
