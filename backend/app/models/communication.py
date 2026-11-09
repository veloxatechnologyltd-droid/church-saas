import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class Communication(Base):
    __tablename__ = "communications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False, default="sms")
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    audience_type = Column(String, nullable=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)
    recipients = Column(Text, nullable=True)  # JSON array of recipient member IDs
    recipient_count = Column(Integer, default=0, nullable=False)
    successful_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    provider_message_id = Column(String, nullable=True)
    credits_used = Column(Integer, nullable=True)
    sent_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    status = Column(String, nullable=False, default="queued")

    group = relationship("Group")


class ReminderSchedule(Base):
    """A recurring weekly message definition, evaluated by the reminder runner."""

    __tablename__ = "reminder_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    message_template = Column(Text, nullable=False)
    frequency = Column(String, nullable=False, default="weekly")
    weekday = Column(Integer, nullable=False)  # Python weekday: Monday=0 ... Sunday=6
    send_time = Column(Time, nullable=False)
    timezone = Column(String, nullable=False, default="Africa/Accra")
    audience_type = Column(String, nullable=False, default="all_members")
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    group = relationship("Group")


class ReminderRun(Base):
    __tablename__ = "reminder_runs"
    __table_args__ = (UniqueConstraint("schedule_id", "scheduled_for", name="uq_reminder_schedule_run"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("reminder_schedules.id", ondelete="CASCADE"), nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    communication_id = Column(UUID(as_uuid=True), ForeignKey("communications.id"), nullable=True)
    status = Column(String, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    schedule = relationship("ReminderSchedule")
    communication = relationship("Communication")
