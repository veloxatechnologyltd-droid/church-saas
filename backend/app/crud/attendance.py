from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.member import Member
from app.schemas.attendance import AttendanceMarkItem, AttendanceSessionCreate


def list_sessions(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[AttendanceSession], int]:
    query = db.query(AttendanceSession)
    total = query.count()
    sessions = query.order_by(AttendanceSession.session_date.desc()).offset(skip).limit(limit).all()
    return sessions, total


def create_session(db: Session, payload: AttendanceSessionCreate, created_by: UUID | None) -> AttendanceSession:
    session = AttendanceSession(**payload.model_dump(), created_by=created_by)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: UUID) -> AttendanceSession | None:
    return db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()


def set_self_checkin(db: Session, session: AttendanceSession, is_open: bool) -> AttendanceSession:
    """Open/close self check-in; generates an unguessable code the first time."""
    if is_open and not session.checkin_code:
        import secrets

        session.checkin_code = secrets.token_urlsafe(8)
    session.checkin_open = is_open
    db.flush()
    return session


def mark_attendance(db: Session, session_id: UUID, records: list[AttendanceMarkItem]) -> list[AttendanceRecord]:
    existing = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id, AttendanceRecord.member_id.in_([r.member_id for r in records]))
        .all()
    )
    existing_map = {(row.session_id, row.member_id): row for row in existing}

    touched: list[AttendanceRecord] = []
    for item in records:
        key = (session_id, item.member_id)
        checked_in_at = datetime.now(timezone.utc) if item.status == "present" else None
        if key in existing_map:
            row = existing_map[key]
            row.status = item.status
            row.checked_in_at = checked_in_at
            row.notes = item.notes
            touched.append(row)
            continue

        row = AttendanceRecord(
            session_id=session_id,
            member_id=item.member_id,
            status=item.status,
            checked_in_at=checked_in_at,
            notes=item.notes,
        )
        db.add(row)
        touched.append(row)

    db.commit()

    for row in touched:
        db.refresh(row)

    return touched


def member_attendance_history(db: Session, member_id: UUID):
    rows = (
        db.query(AttendanceRecord, AttendanceSession)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .filter(AttendanceRecord.member_id == member_id)
        .order_by(AttendanceSession.session_date.desc())
        .all()
    )

    total_sessions = db.query(func.count(AttendanceSession.id)).scalar() or 0
    present_count = sum(1 for record, _ in rows if record.status == "present")
    percentage = round((present_count / total_sessions) * 100, 2) if total_sessions else 0.0

    history = [
        {
            "session_id": session.id,
            "session_title": session.title,
            "session_type": session.session_type,
            "session_date": session.session_date,
            "session_start_time": session.session_start_time,
            "status": record.status,
            "checked_in_at": record.checked_in_at,
            "notes": record.notes,
        }
        for record, session in rows
    ]
    return history, percentage


def _session_start_datetime(session_date: date, session_start_time: time | None) -> datetime | None:
    if not session_start_time:
        return None
    return datetime.combine(session_date, session_start_time, tzinfo=timezone.utc)


def member_activity_summary(db: Session, member_id: UUID) -> dict:
    history, attendance_percentage = member_attendance_history(db, member_id)
    total_records = len(history)
    present_count = sum(1 for row in history if row["status"] == "present")
    absent_count = sum(1 for row in history if row["status"] == "absent")
    excused_count = sum(1 for row in history if row["status"] == "excused")
    last_present = next((row for row in history if row["status"] == "present"), None)
    punctuality_rows = [row for row in history if row["status"] == "present" and row["checked_in_at"] and row["session_start_time"]]
    grace_period = timedelta(minutes=15)
    on_time_count = 0
    late_count = 0
    for row in punctuality_rows:
        start_at = _session_start_datetime(row["session_date"], row["session_start_time"])
        if not start_at:
            continue
        checked_in_at = row["checked_in_at"]
        if checked_in_at <= start_at + grace_period:
            on_time_count += 1
        else:
            late_count += 1
    punctuality_rate = round((on_time_count / len(punctuality_rows)) * 100, 2) if punctuality_rows else 0.0

    return {
        "attendance_percentage": attendance_percentage,
        "total_sessions_marked": total_records,
        "present_count": present_count,
        "absent_count": absent_count,
        "excused_count": excused_count,
        "last_present_date": last_present["session_date"] if last_present else None,
        "punctuality_tracked": bool(punctuality_rows),
        "punctuality_note": "Punctuality is measured from session start time with a 15-minute grace period.",
        "on_time_count": on_time_count,
        "late_count": late_count,
        "punctuality_rate": punctuality_rate,
        "history": history[:12],
    }


def attendance_summary(db: Session):
    total_sessions = db.query(func.count(AttendanceSession.id)).scalar() or 0

    status_counts = defaultdict(int)
    status_rows = db.query(AttendanceRecord.status, func.count(AttendanceRecord.id)).group_by(AttendanceRecord.status).all()
    for status, count in status_rows:
        status_counts[status] = count

    member_stats = (
        db.query(
            AttendanceRecord.member_id,
            func.sum(case((AttendanceRecord.status == "present", 1), else_=0)).label("present_count"),
            func.count(AttendanceRecord.id).label("record_count"),
        )
        .group_by(AttendanceRecord.member_id)
        .all()
    )

    low_attendance_members = 0
    for row in member_stats:
        ratio = (row.present_count / row.record_count) if row.record_count else 0
        if ratio < 0.5:
            low_attendance_members += 1

    return {
        "total_members": db.query(func.count(Member.id)).scalar() or 0,
        "total_sessions": total_sessions,
        "present_count": status_counts["present"],
        "absent_count": status_counts["absent"],
        "excused_count": status_counts["excused"],
        "low_attendance_members": low_attendance_members,
    }
