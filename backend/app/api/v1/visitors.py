"""First-time visitors: capture, follow-up and conversion to members."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.crud import visitor as visitor_crud
from app.db.database import get_db
from app.models.membership import Membership
from app.models.user import User
from app.schemas.member import MemberResponse
from app.schemas.outreach import VisitorContacted, VisitorCreate, VisitorResponse, VisitorUpdate
from app.services.audit import record_audit

router = APIRouter()

READ_ROLES = ("church_admin", "secretary", "group_leader")
WRITE_ROLES = ("church_admin", "secretary")


def _serialize(visitor) -> dict:
    data = VisitorResponse.model_validate(visitor).model_dump(mode="json")
    data["assignee_email"] = visitor.assignee.email if visitor.assignee else None
    return data


def _get_or_404(db: Session, visitor_id: UUID):
    visitor = visitor_crud.get_visitor(db, visitor_id)
    if visitor is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


def _check_assignee(db: Session, user_id: UUID | None) -> None:
    """The assignee must be an active user of this church (memberships are tenant-scoped)."""
    if user_id is None:
        return
    found = (
        db.query(User.id)
        .join(Membership, Membership.user_id == User.id)
        .filter(User.id == user_id, Membership.is_active.is_(True))
        .first()
    )
    if found is None:
        raise HTTPException(status_code=400, detail="Assignee is not a member of this church's team")


@router.get("/summary")
def visitor_summary(db: Session = Depends(get_db), current_user=Depends(require_roles(*READ_ROLES))):
    return {"status": "success", "data": visitor_crud.visitor_summary(db)}


@router.get("/")
def list_visitors(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*READ_ROLES)),
):
    rows, total = visitor_crud.list_visitors(db, status=status_filter, search=search, skip=skip, limit=limit)
    return {
        "status": "success",
        "data": [_serialize(v) for v in rows],
        "total": total,
        "page": (skip // limit) + 1,
        "limit": limit,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_visitor(
    payload: VisitorCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WRITE_ROLES)),
):
    _check_assignee(db, payload.assigned_to)
    visitor = visitor_crud.create_visitor(db, payload)
    record_audit(db, user_id=current_user.id, action="created", table_name="visitors", record_id=visitor.id,
                 new_value={"first_name": visitor.first_name, "last_name": visitor.last_name})
    db.commit()
    db.refresh(visitor)
    return {"status": "success", "data": _serialize(visitor)}


@router.get("/{visitor_id}")
def get_visitor(visitor_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles(*READ_ROLES))):
    return {"status": "success", "data": _serialize(_get_or_404(db, visitor_id))}


@router.put("/{visitor_id}")
def update_visitor(
    visitor_id: UUID,
    payload: VisitorUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WRITE_ROLES)),
):
    visitor = _get_or_404(db, visitor_id)
    if "assigned_to" in payload.model_fields_set:
        _check_assignee(db, payload.assigned_to)
    visitor_crud.update_visitor(db, visitor, payload)
    record_audit(db, user_id=current_user.id, action="updated", table_name="visitors", record_id=visitor.id,
                 new_value=payload.model_dump(mode="json", exclude_unset=True))
    db.commit()
    db.refresh(visitor)
    return {"status": "success", "data": _serialize(visitor)}


@router.delete("/{visitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visitor(visitor_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles(*WRITE_ROLES))):
    visitor = _get_or_404(db, visitor_id)
    db.delete(visitor)
    record_audit(db, user_id=current_user.id, action="deleted", table_name="visitors", record_id=visitor_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{visitor_id}/contacted")
def mark_contacted(
    visitor_id: UUID,
    payload: VisitorContacted | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WRITE_ROLES)),
):
    visitor = _get_or_404(db, visitor_id)
    visitor_crud.mark_contacted(db, visitor, payload.notes if payload else None)
    record_audit(db, user_id=current_user.id, action="contacted", table_name="visitors", record_id=visitor.id)
    db.commit()
    db.refresh(visitor)
    return {"status": "success", "data": _serialize(visitor)}


@router.post("/{visitor_id}/convert")
def convert_visitor(visitor_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles(*WRITE_ROLES))):
    visitor = _get_or_404(db, visitor_id)
    if visitor.converted_member_id:
        raise HTTPException(status_code=409, detail="This visitor is already a member")
    member = visitor_crud.convert_to_member(db, visitor)
    record_audit(db, user_id=current_user.id, action="converted", table_name="visitors", record_id=visitor.id,
                 new_value={"member_id": str(member.id)})
    record_audit(db, user_id=current_user.id, action="created", table_name="members", record_id=member.id,
                 new_value={"first_name": member.first_name, "last_name": member.last_name, "from_visitor": str(visitor.id)})
    db.commit()
    db.refresh(visitor)
    db.refresh(member)
    return {
        "status": "success",
        "data": {"visitor": _serialize(visitor), "member": MemberResponse.model_validate(member).model_dump(mode="json")},
    }
