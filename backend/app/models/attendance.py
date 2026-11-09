import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique, same_church_fk


class AttendanceSession(ChurchScoped, Base):
    __tablename__ = "attendance_sessions"
    __table_args__ = (
        id_church_unique("attendance_sessions"),
        same_church_fk("attendance_sessions", "branch_id", "branches"),
        Index("ix_attendance_sessions_church_date", "church_id", "session_date"),
        UniqueConstraint("checkin_code", name="uq_attendance_sessions_checkin_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    session_date = Column(Date, nullable=False)
    session_type = Column(String, nullable=True)
    session_start_time = Column(Time, nullable=True)
    notes = Column(Text, nullable=True)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    # Self check-in: members open /checkin/<code> (QR on the screen) and enter their phone.
    checkin_code = Column(String, nullable=True)
    checkin_open = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    first_timer_count = Column(Integer, nullable=False, default=0, server_default="0")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    records = relationship(
        "AttendanceRecord", back_populates="session", foreign_keys="AttendanceRecord.session_id"
    )


class AttendanceRecord(ChurchScoped, Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "member_id", name="uq_session_member"),
        same_church_fk("attendance_records", "session_id", "attendance_sessions"),
        same_church_fk("attendance_records", "member_id", "members"),
        Index("ix_attendance_records_church_session", "church_id", "session_id"),
        Index("ix_attendance_records_church_member", "church_id", "member_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    member_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String, nullable=False, default="manual", server_default="manual")  # manual, self_checkin
    notes = Column(Text, nullable=True)

    session = relationship("AttendanceSession", back_populates="records", foreign_keys=[session_id])
    member = relationship("Member", back_populates="attendance_records", foreign_keys=[member_id])
