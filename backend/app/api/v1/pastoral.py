from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.crud import pastoral as pastoral_crud
from app.db.database import get_db
from app.models.member import Member
from app.models.membership import Membership
from app.models.user import User
from app.schemas.pastoral import PastoralLogCreate, PastoralLogResponse, PastoralLogUpdate
from app.services.audit import record_audit

router = APIRouter()
PASTORAL_ROLES = ("church_admin", "secretary", "group_leader")


def _serialize(row) -> dict:
    return PastoralLogResponse(
        id=row.id,
        member_id=row.member_id,
        member_name=f"{row.member.first_name} {row.member.last_name}".strip() if row.member else None,
        member_status=row.member.membership_status if row.member else None,
        member_phone=row.member.phone if row.member else None,
        log_type=row.log_type,
        notes=row.notes,
        status=row.status,
        priority=row.priority,
        source=row.source,
        follow_up_date=row.follow_up_date,
        due_state=pastoral_crud.due_state(row.follow_up_date, row.status),
        assigned_to=row.assigned_to,
        assignee_name=row.assignee.email if row.assignee else None,
        logged_by=row.logged_by,
        log_date=row.log_date,
        completed_at=row.completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump()


def _validate_assignee(db: Session, church_id: UUID, assignee_id: UUID | None) -> None:
    """The care owner must be an active staff member of the SAME church."""
    if not assignee_id:
        return
    assignee = (
        db.query(User)
        .join(Membership, Membership.user_id == User.id)
        .filter(
            User.id == assignee_id,
            User.is_active.is_(True),
            Membership.church_id == church_id,
            Membership.is_active.is_(True),
            Membership.role.in_(PASTORAL_ROLES),
        )
        .first()
    )
    if not assignee:
        raise HTTPException(status_code=400, detail="Selected care owner is not available")


@router.get("/")
def list_pastoral_logs(
    member_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    assigned_to: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*PASTORAL_ROLES)),
):
    assignee_filter = current_user.id if current_user.role == "group_leader" else assigned_to
    rows = pastoral_crud.list_logs(
        db,
        member_id=member_id,
        status=status_filter,
        priority=priority,
        assigned_to=assignee_filter,
    )
    return {"status": "success", "data": [_serialize(row) for row in rows], "total": len(rows)}


@router.get("/summary")
def pastoral_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*PASTORAL_ROLES)),
):
    assigned_to = current_user.id if current_user.role == "group_leader" else None
    return {"status": "success", "data": pastoral_crud.summary(db, assigned_to=assigned_to)}


@router.get("/attendance-risks")
def attendance_risks(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    rows = pastoral_crud.list_attendance_risks(db, limit=limit)
    return {"status": "success", "data": rows, "total": len(rows)}


@router.get("/assignees")
def pastoral_assignees(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    rows = pastoral_crud.list_assignees(db, current_user.church_id)
    return {
        "status": "success",
        "data": [
            {"id": row.id, "email": row.email, "role": row.role}
            for row in rows
        ],
        "total": len(rows),
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_pastoral_log(
    payload: PastoralLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    if not db.query(Member).filter(Member.id == payload.member_id).first():
        raise HTTPException(status_code=404, detail="Member not found")
    _validate_assignee(db, current_user.church_id, payload.assigned_to)
    row = pastoral_crud.create_log(db, payload, current_user.id)
    record_audit(
        db,
        user_id=current_user.id,
        action="created",
        table_name="pastoral_logs",
        record_id=row.id,
        new_value={
            "member_id": str(row.member_id),
            "log_type": row.log_type,
            "status": row.status,
            "priority": row.priority,
            "assigned_to": str(row.assigned_to) if row.assigned_to else None,
        },
    )
    db.commit()
    return {"status": "success", "data": _serialize(row)}


@router.put("/{log_id}")
def update_pastoral_log(
    log_id: UUID,
    payload: PastoralLogUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*PASTORAL_ROLES)),
):
    existing = pastoral_crud.get_log(db, log_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pastoral log not found")
    if current_user.role == "group_leader":
        if existing.assigned_to != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update care assigned to you")
        if "assigned_to" in payload.model_fields_set and payload.assigned_to != current_user.id:
            raise HTTPException(status_code=403, detail="You cannot reassign this follow-up")
    else:
        _validate_assignee(db, current_user.church_id, payload.assigned_to)
    row = pastoral_crud.update_log(db, log_id, payload)
    record_audit(db, user_id=current_user.id, action="updated", table_name="pastoral_logs", record_id=log_id, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return {"status": "success", "data": _serialize(row)}
