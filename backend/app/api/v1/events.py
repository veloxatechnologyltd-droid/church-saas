from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.crud import communication as communication_crud
from app.crud import event as event_crud
from app.db.database import get_db
from app.models.member import Member
from app.schemas.communication import SMSCreate
from app.schemas.event import EventCreate, EventRegistrationCreate, EventRegistrationResponse, EventReminderRequest, EventResponse, EventUpdate
from app.services.audit import record_audit

router = APIRouter()


@router.get("/health")
def events_health() -> dict:
    return {"status": "success", "data": {"module": "events", "health": "ok"}}


def _serialize_event(db: Session, event) -> dict:
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        location=event.location,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        is_recurring=event.is_recurring,
        recurrence_rule=event.recurrence_rule,
        max_capacity=event.max_capacity,
        registration_count=event_crud.registration_count(db, event.id),
        created_by=event.created_by,
        created_at=event.created_at,
        updated_at=event.updated_at,
    ).model_dump()


@router.get("/")
def list_events(
    upcoming_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    events = event_crud.list_events(db, upcoming_only=upcoming_only)
    return {"status": "success", "data": [_serialize_event(db, event) for event in events], "total": len(events)}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    event = event_crud.create_event(db, payload, current_user.id)
    record_audit(db, user_id=current_user.id, action="created", table_name="events", record_id=event.id, new_value={"title": event.title})
    db.commit()
    return {"status": "success", "data": _serialize_event(db, event)}


@router.get("/{event_id}")
def get_event(event_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = event_crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "success", "data": _serialize_event(db, event)}


@router.put("/{event_id}")
def update_event(
    event_id: UUID,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    event = event_crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    old_value = {"title": event.title, "start_datetime": event.start_datetime.isoformat()}
    updated = event_crud.update_event(db, event_id, payload)
    record_audit(db, user_id=current_user.id, action="updated", table_name="events", record_id=event_id, old_value=old_value, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return {"status": "success", "data": _serialize_event(db, updated)}


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    if not event_crud.delete_event(db, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    record_audit(db, user_id=current_user.id, action="deleted", table_name="events", record_id=event_id)
    db.commit()


@router.post("/{event_id}/register", status_code=status.HTTP_201_CREATED)
def register_for_event(
    event_id: UUID,
    payload: EventRegistrationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    event = event_crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user.role == "member" and current_user.member_id != payload.member_id:
        raise HTTPException(status_code=403, detail="Members can only register themselves")
    if not db.query(Member).filter(Member.id == payload.member_id).first():
        raise HTTPException(status_code=404, detail="Member not found")
    if event.max_capacity and event_crud.registration_count(db, event_id) >= event.max_capacity:
        raise HTTPException(status_code=400, detail="Event capacity has been reached")
    try:
        registration = event_crud.register_member(db, event_id, payload.member_id)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Member is already registered for this event") from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="event_registrations", record_id=registration.id, new_value={"event_id": str(event_id), "member_id": str(payload.member_id)})
    db.commit()
    return {"status": "success", "data": {"id": registration.id, "event_id": event_id, "member_id": registration.member_id, "registered_at": registration.registered_at}}


@router.get("/{event_id}/registrations")
def event_registrations(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    if not event_crud.get_event(db, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    rows = event_crud.list_registrations(db, event_id)
    data = [
        EventRegistrationResponse(
            id=row.id,
            event_id=row.event_id,
            member_id=row.member_id,
            member_name=f"{row.member.first_name} {row.member.last_name}".strip(),
            phone=row.member.phone,
            registered_at=row.registered_at,
        ).model_dump()
        for row in rows
    ]
    return {"status": "success", "data": data, "total": len(data)}


@router.post("/{event_id}/remind")
def remind_event_registrants(
    event_id: UUID,
    payload: EventReminderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    event = event_crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    registrations = event_crud.list_registrations(db, event_id)
    if not registrations:
        raise HTTPException(status_code=400, detail="There are no registered members to remind")
    message = payload.message or f"Reminder: {event.title} is scheduled for {event.start_datetime.strftime('%d %b %Y at %H:%M')}."
    sms_payload = SMSCreate(message=message, audience_type="selected_members", member_ids=[row.member_id for row in registrations])
    try:
        communication = communication_crud.send_sms_and_log(db, sms_payload, current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "success", "data": {"communication_id": communication.id, "recipient_count": communication.recipient_count, "successful_count": communication.successful_count, "status": communication.status}}
