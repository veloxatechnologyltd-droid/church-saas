import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.communication import Communication, ReminderRun, ReminderSchedule
from app.models.group import Group, GroupMember
from app.models.member import Member
from app.schemas.communication import ReminderScheduleCreate, ReminderScheduleUpdate, SMSCreate
from app.services.sms import send_sms


def _membership_status_for_audience(audience_type: str) -> str | None:
    if audience_type == "active_members":
        return "active"
    if audience_type == "inactive_members":
        return "inactive"
    return None


def resolve_recipients(db: Session, audience_type: str, group_id: UUID | None = None, member_ids: list[UUID] | None = None):
    query = db.query(Member).filter(Member.phone.isnot(None), Member.phone != "")
    membership_status = _membership_status_for_audience(audience_type)
    if membership_status:
        query = query.filter(Member.membership_status == membership_status)
    if audience_type == "department":
        query = query.join(GroupMember, GroupMember.member_id == Member.id).filter(GroupMember.group_id == group_id)
    elif audience_type == "selected_members":
        query = query.filter(Member.id.in_(member_ids or []))
    return query.order_by(Member.first_name.asc(), Member.last_name.asc()).all()


def _create_communication_log(
    db: Session,
    payload: SMSCreate,
    members: list[Member],
    sent_by: UUID | None,
) -> Communication:
    communication = Communication(
        type="sms",
        body=payload.message,
        audience_type=payload.audience_type,
        group_id=payload.group_id,
        recipients=json.dumps([str(member.id) for member in members]),
        recipient_count=len(members),
        sent_by=sent_by,
        status="queued",
    )
    db.add(communication)
    db.flush()
    return communication


def send_sms_and_log(db: Session, payload: SMSCreate, sent_by: UUID | None) -> Communication:
    members = resolve_recipients(db, payload.audience_type, payload.group_id, payload.member_ids)
    communication = _create_communication_log(db, payload, members, sent_by)
    if not members:
        communication.status = "skipped"
        db.commit()
        db.refresh(communication)
        return communication

    try:
        result = send_sms([member.phone for member in members if member.phone], payload.message)
        communication.successful_count = result.successful_count
        communication.failed_count = result.failed_count
        communication.provider_message_id = result.provider_message_id
        communication.credits_used = result.credits_used
        communication.status = "sent" if result.failed_count == 0 else "partial"
    except Exception as exc:
        communication.status = "failed"
        communication.failed_count = len(members)
        db.commit()
        raise RuntimeError(str(exc)) from exc

    db.commit()
    db.refresh(communication)
    return communication


def list_communications(db: Session, limit: int = 50) -> list[Communication]:
    return db.query(Communication).order_by(Communication.sent_at.desc()).limit(limit).all()


def list_schedules(db: Session, include_inactive: bool = False) -> list[ReminderSchedule]:
    query = db.query(ReminderSchedule)
    if not include_inactive:
        query = query.filter(ReminderSchedule.is_active.is_(True))
    return query.order_by(ReminderSchedule.weekday.asc(), ReminderSchedule.send_time.asc()).all()


def get_schedule(db: Session, schedule_id: UUID) -> ReminderSchedule | None:
    return db.query(ReminderSchedule).filter(ReminderSchedule.id == schedule_id).first()


def create_schedule(db: Session, payload: ReminderScheduleCreate, created_by: UUID | None) -> ReminderSchedule:
    schedule = ReminderSchedule(**payload.model_dump(), created_by=created_by)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule(db: Session, schedule_id: UUID, payload: ReminderScheduleUpdate) -> ReminderSchedule | None:
    schedule = get_schedule(db, schedule_id)
    if not schedule:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("audience_type") and updates["audience_type"] != "department":
        updates["group_id"] = None
    for field, value in updates.items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


def deactivate_schedule(db: Session, schedule_id: UUID) -> bool:
    schedule = get_schedule(db, schedule_id)
    if not schedule:
        return False
    schedule.is_active = False
    db.commit()
    return True


def _scheduled_datetime(schedule: ReminderSchedule, now: datetime) -> datetime | None:
    try:
        zone = ZoneInfo(schedule.timezone)
    except Exception:
        return None
    local_now = now.astimezone(zone)
    if local_now.weekday() != schedule.weekday:
        return None
    if schedule.start_date and local_now.date() < schedule.start_date:
        return None
    if schedule.end_date and local_now.date() > schedule.end_date:
        return None
    scheduled_local = datetime.combine(local_now.date(), schedule.send_time, tzinfo=zone)
    return scheduled_local.astimezone(timezone.utc)


def run_due_reminders(db: Session, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    results = []
    for schedule in list_schedules(db):
        scheduled_for = _scheduled_datetime(schedule, now)
        if scheduled_for is None or not (now - timedelta(minutes=15) <= scheduled_for <= now):
            continue
        try:
            run = ReminderRun(schedule_id=schedule.id, scheduled_for=scheduled_for, status="running")
            db.add(run)
            db.commit()
            db.refresh(run)
        except IntegrityError:
            db.rollback()
            continue

        payload = SMSCreate(
            message=schedule.message_template,
            audience_type=schedule.audience_type,
            group_id=schedule.group_id,
        )
        try:
            communication = send_sms_and_log(db, payload, schedule.created_by)
            run.communication_id = communication.id
            run.status = communication.status
            schedule.last_run_at = now
            db.commit()
            results.append({"schedule_id": str(schedule.id), "status": run.status, "communication_id": str(communication.id)})
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            schedule.last_run_at = now
            db.commit()
            results.append({"schedule_id": str(schedule.id), "status": "failed", "error": str(exc)})
    return results
