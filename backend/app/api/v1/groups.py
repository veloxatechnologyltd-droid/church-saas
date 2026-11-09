from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.crud import group as group_crud
from app.db.database import get_db
from app.models.member import Member
from app.schemas.group import GroupCreate, GroupMemberCreate, GroupMemberResponse, GroupResponse, GroupUpdate
from app.services.audit import record_audit

router = APIRouter()


@router.get("/health")
def groups_health() -> dict:
    return {"status": "success", "data": {"module": "groups", "health": "ok"}}


def _can_manage_group(current_user, group) -> bool:
    return current_user.role in {"church_admin", "secretary"} or (
        current_user.role == "group_leader" and current_user.member_id == group.leader_id
    )


def _serialize_group(db: Session, group) -> dict:
    leader_name = None
    if group.leader:
        leader_name = f"{group.leader.first_name} {group.leader.last_name}".strip()
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "leader_id": group.leader_id,
        "leader_name": leader_name,
        "member_count": group_crud.group_member_count(db, group.id),
        "is_active": group.is_active,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


@router.get("/")
def list_groups(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    groups = group_crud.list_groups(db, include_inactive=include_inactive and current_user.role == "church_admin")
    return {"status": "success", "data": [_serialize_group(db, group) for group in groups], "total": len(groups)}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    try:
        group = group_crud.create_group(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with this name already exists") from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="groups", record_id=group.id, new_value={"name": group.name})
    db.commit()
    return {"status": "success", "data": _serialize_group(db, group)}


@router.get("/{group_id}")
def get_group(group_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    group = group_crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Department not found")
    return {"status": "success", "data": _serialize_group(db, group)}


@router.put("/{group_id}")
def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    existing = group_crud.get_group(db, group_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found")
    old_value = {"name": existing.name, "leader_id": str(existing.leader_id) if existing.leader_id else None}
    try:
        group = group_crud.update_group(db, group_id, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with this name already exists") from exc
    record_audit(db, user_id=current_user.id, action="updated", table_name="groups", record_id=group.id, old_value=old_value, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return {"status": "success", "data": _serialize_group(db, group)}


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    if not group_crud.deactivate_group(db, group_id):
        raise HTTPException(status_code=404, detail="Department not found")
    record_audit(db, user_id=current_user.id, action="deactivated", table_name="groups", record_id=group_id)
    db.commit()


@router.get("/{group_id}/members")
def list_group_members(group_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    group = group_crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Department not found")
    memberships = group_crud.list_group_members(db, group_id)
    data = [
        GroupMemberResponse(
            id=membership.id,
            member_id=membership.member_id,
            member_name=f"{membership.member.first_name} {membership.member.last_name}".strip(),
            phone=membership.member.phone,
            joined_at=membership.joined_at,
        ).model_dump()
        for membership in memberships
    ]
    return {"status": "success", "data": data, "total": len(data)}


@router.post("/{group_id}/members", status_code=status.HTTP_201_CREATED)
def add_group_member(
    group_id: UUID,
    payload: GroupMemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    group = group_crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Department not found")
    if not _can_manage_group(current_user, group):
        raise HTTPException(status_code=403, detail="You cannot manage this department")
    if not db.query(Member).filter(Member.id == payload.member_id).first():
        raise HTTPException(status_code=404, detail="Member not found")
    try:
        membership = group_crud.add_member(db, group_id, payload.member_id)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Member is already in this department") from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="group_members", record_id=membership.id, new_value={"group_id": str(group_id), "member_id": str(payload.member_id)})
    db.commit()
    return {
        "status": "success",
        "data": {"id": membership.id, "group_id": group_id, "member_id": membership.member_id, "joined_at": membership.joined_at},
    }


@router.delete("/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_group_member(
    group_id: UUID,
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    group = group_crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Department not found")
    if not _can_manage_group(current_user, group):
        raise HTTPException(status_code=403, detail="You cannot manage this department")
    if not group_crud.remove_member(db, group_id, member_id):
        raise HTTPException(status_code=404, detail="Member is not in this department")
    record_audit(db, user_id=current_user.id, action="deleted", table_name="group_members", new_value={"group_id": str(group_id), "member_id": str(member_id)})
    db.commit()
