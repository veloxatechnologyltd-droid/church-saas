from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import GROUP_ROLES, MESSAGING_ROLES, get_current_user, require_roles
from app.core.config import settings
from app.crud import communication as communication_crud
from app.crud import announcement as announcement_crud
from app.db.database import get_db
from app.models.group import Group
from app.schemas.communication import (
    CommunicationResponse,
    ReminderScheduleCreate,
    ReminderScheduleResponse,
    ReminderScheduleUpdate,
    SMSCreate,
)
from app.schemas.announcement import AnnouncementCreate, AnnouncementResponse, AnnouncementUpdate
from app.services.audit import record_audit

router = APIRouter()


@router.get("/health")
def communication_health() -> dict:
    provider = settings.SMS_PROVIDER.strip().lower()
    configured = (
        bool(settings.ARKESEL_API_KEY)
        if provider == "arkesel"
        else bool(settings.MOOLRE_VAS_KEY)
        if provider == "moolre"
        else False
    )
    return {
        "status": "success",
        "data": {
            "module": "communication",
            "health": "ok",
            "sms_provider": provider,
            "sms_provider_supported": provider in {"arkesel", "moolre"},
            "sms_provider_configured": configured,
        },
    }


def _serialize_communication(communication) -> dict:
    return CommunicationResponse.model_validate(communication).model_dump()


def _serialize_schedule(schedule) -> dict:
    return ReminderScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        message_template=schedule.message_template,
        frequency=schedule.frequency,
        weekday=schedule.weekday,
        send_time=schedule.send_time,
        timezone=schedule.timezone,
        audience_type=schedule.audience_type,
        group_id=schedule.group_id,
        group_name=schedule.group.name if schedule.group else None,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    ).model_dump()


def _serialize_announcement(announcement) -> dict:
    return AnnouncementResponse.model_validate(announcement).model_dump()


def _can_manage_group(current_user, group: Group | None) -> bool:
    return bool(
        group
        and (
            current_user.role in {"church_admin", "secretary"}
            or (current_user.role == "group_leader" and current_user.member_id == group.leader_id)
        )
    )


def _validate_audience_scope(payload, current_user, db: Session) -> None:
    if current_user.role not in {"church_admin", "secretary", "group_leader"}:
        raise HTTPException(status_code=403, detail="You do not have permission to send SMS")
    if current_user.role != "group_leader":
        return
    if payload.audience_type != "department" or not payload.group_id:
        raise HTTPException(status_code=403, detail="Department leaders can only message their own department")
    group = db.query(Group).filter(Group.id == payload.group_id, Group.is_active.is_(True)).first()
    if not _can_manage_group(current_user, group):
        raise HTTPException(status_code=403, detail="You cannot message this department")


@router.post("/sms", status_code=status.HTTP_201_CREATED)
def send_bulk_sms(
    payload: SMSCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GROUP_ROLES)),
):
    _validate_audience_scope(payload, current_user, db)
    try:
        communication = communication_crud.send_sms_and_log(db, payload, current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="sent", table_name="communications", record_id=communication.id, new_value={"audience_type": communication.audience_type, "recipient_count": communication.recipient_count, "status": communication.status})
    db.commit()
    return {"status": "success", "data": _serialize_communication(communication)}


@router.get("/history")
def communication_history(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    communications = communication_crud.list_communications(db, limit=limit)
    return {"status": "success", "data": [_serialize_communication(item) for item in communications], "total": len(communications)}


@router.get("/reminders")
def list_reminders(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MESSAGING_ROLES)),
):
    schedules = communication_crud.list_schedules(
        db,
        include_inactive=include_inactive and current_user.role in {"church_admin", "secretary"},
    )
    if current_user.role == "group_leader":
        schedules = [schedule for schedule in schedules if schedule.group and schedule.group.leader_id == current_user.member_id]
    return {"status": "success", "data": [_serialize_schedule(item) for item in schedules], "total": len(schedules)}


@router.post("/reminders", status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: ReminderScheduleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MESSAGING_ROLES)),
):
    if current_user.role not in {"church_admin", "secretary", "group_leader"}:
        raise HTTPException(status_code=403, detail="You do not have permission to create reminders")
    if payload.audience_type == "department":
        group = db.query(Group).filter(Group.id == payload.group_id, Group.is_active.is_(True)).first()
        if not group:
            raise HTTPException(status_code=404, detail="Department not found")
        if current_user.role == "group_leader" and not _can_manage_group(current_user, group):
            raise HTTPException(status_code=403, detail="You cannot schedule messages for this department")
    elif current_user.role == "group_leader":
        raise HTTPException(status_code=403, detail="Department leaders can only schedule messages for their department")
    schedule = communication_crud.create_schedule(db, payload, current_user.id)
    record_audit(db, user_id=current_user.id, action="created", table_name="reminder_schedules", record_id=schedule.id, new_value={"name": schedule.name, "weekday": schedule.weekday, "send_time": schedule.send_time.isoformat()})
    db.commit()
    return {"status": "success", "data": _serialize_schedule(schedule)}


@router.put("/reminders/{schedule_id}")
def update_reminder(
    schedule_id: UUID,
    payload: ReminderScheduleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MESSAGING_ROLES)),
):
    if current_user.role not in {"church_admin", "secretary", "group_leader"}:
        raise HTTPException(status_code=403, detail="You do not have permission to update reminders")
    schedule = communication_crud.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if current_user.role == "group_leader":
        if schedule.audience_type != "department" or not schedule.group or not _can_manage_group(current_user, schedule.group):
            raise HTTPException(status_code=403, detail="You cannot manage this reminder")
        if (payload.audience_type and payload.audience_type != "department") or (payload.group_id and payload.group_id != schedule.group_id):
            raise HTTPException(status_code=403, detail="You can only manage reminders for your department")
    if payload.audience_type == "department":
        group = db.query(Group).filter(Group.id == payload.group_id, Group.is_active.is_(True)).first()
        if not group:
            raise HTTPException(status_code=404, detail="Department not found")
        if current_user.role == "group_leader" and not _can_manage_group(current_user, group):
            raise HTTPException(status_code=403, detail="You cannot schedule messages for this department")
    elif payload.audience_type and current_user.role == "group_leader":
        raise HTTPException(status_code=403, detail="Department leaders can only message their department")
    updated = communication_crud.update_schedule(db, schedule_id, payload)
    record_audit(db, user_id=current_user.id, action="updated", table_name="reminder_schedules", record_id=schedule_id, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return {"status": "success", "data": _serialize_schedule(updated)}


@router.delete("/reminders/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MESSAGING_ROLES)),
):
    schedule = communication_crud.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if current_user.role == "group_leader" and (not schedule.group or not _can_manage_group(current_user, schedule.group)):
        raise HTTPException(status_code=403, detail="You cannot manage this reminder")
    if current_user.role not in {"church_admin", "secretary", "group_leader"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    communication_crud.deactivate_schedule(db, schedule_id)
    record_audit(db, user_id=current_user.id, action="deactivated", table_name="reminder_schedules", record_id=schedule_id)
    db.commit()


@router.post("/reminders/run-due")
def run_due_reminders(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    results = communication_crud.run_due_reminders(db)
    return {"status": "success", "data": results, "total": len(results)}


@router.post("/announcement", status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    announcement = announcement_crud.create_announcement(db, payload, current_user.id)
    record_audit(
        db,
        user_id=current_user.id,
        action="created",
        table_name="announcements",
        record_id=announcement.id,
        new_value={"title": announcement.title, "is_active": announcement.is_active},
    )
    db.commit()
    return {"status": "success", "data": _serialize_announcement(announcement)}


@router.get("/announcements")
def list_announcements(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if include_inactive and current_user.role not in {"church_admin", "secretary"}:
        raise HTTPException(status_code=403, detail="Only administrators can view inactive announcements")
    announcements = announcement_crud.list_announcements(db, include_inactive=include_inactive)
    return {"status": "success", "data": [_serialize_announcement(item) for item in announcements], "total": len(announcements)}


@router.put("/announcements/{announcement_id}")
def update_announcement(
    announcement_id: UUID,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    announcement = announcement_crud.update_announcement(db, announcement_id, payload)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    record_audit(db, user_id=current_user.id, action="updated", table_name="announcements", record_id=announcement.id, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return {"status": "success", "data": _serialize_announcement(announcement)}


@router.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    if not announcement_crud.deactivate_announcement(db, announcement_id):
        raise HTTPException(status_code=404, detail="Announcement not found")
    record_audit(db, user_id=current_user.id, action="deactivated", table_name="announcements", record_id=announcement_id)
    db.commit()
