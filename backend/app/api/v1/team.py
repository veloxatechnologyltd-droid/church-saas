"""Team: the logins (memberships) of the active church and their roles."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, require_admin_not_support, require_roles
from app.db.database import get_db
from app.models.church import Branch
from app.models.membership import CHURCH_ROLES, Membership
from app.services.audit import record_audit
from app.services.plans import enforce_limit

router = APIRouter()


class TeamUpdate(BaseModel):
    role: Optional[str] = None
    branch_id: Optional[UUID] = None
    is_active: Optional[bool] = None


def _serialize(m: Membership) -> dict:
    member = m.member
    return {
        "membership_id": str(m.id),
        "user_id": str(m.user_id),
        "email": m.user.email if m.user else None,
        "role": m.role,
        "branch_id": str(m.branch_id) if m.branch_id else None,
        "branch_name": m.branch.name if m.branch else None,
        "member_id": str(m.member_id) if m.member_id else None,
        "member_name": f"{member.first_name} {member.last_name}" if member else None,
        "is_active": m.is_active,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _active_admins(db: Session) -> int:
    return (
        db.query(Membership)
        .filter(Membership.role == "church_admin", Membership.is_active.is_(True), Membership.branch_id.is_(None))
        .count()
    )


@router.get("")
def list_team(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_roles("church_admin"))):
    query = db.query(Membership)
    if current_user.branch_id:
        query = query.filter(Membership.branch_id == current_user.branch_id)
    rows = query.order_by(Membership.created_at).all()
    return {"status": "success", "data": [_serialize(m) for m in rows], "total": len(rows)}


@router.put("/{membership_id}")
def update_team_member(
    membership_id: UUID,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin_not_support),
):
    membership = db.query(Membership).filter(Membership.id == membership_id).first()
    if membership is None or (current_user.branch_id and membership.branch_id != current_user.branch_id):
        raise HTTPException(status_code=404, detail="Team member not found")
    changes = payload.model_dump(exclude_unset=True)

    if "role" in changes and changes["role"] not in CHURCH_ROLES:
        raise HTTPException(status_code=422, detail=f"Role must be one of: {', '.join(CHURCH_ROLES)}")
    if changes.get("branch_id"):
        if current_user.branch_id and changes["branch_id"] != current_user.branch_id:
            raise HTTPException(status_code=403, detail="You can only assign your own branch")
        if db.query(Branch.id).filter(Branch.id == changes["branch_id"]).first() is None:
            raise HTTPException(status_code=404, detail="Branch not found")
    if current_user.branch_id and "branch_id" in changes and changes["branch_id"] is None:
        raise HTTPException(status_code=403, detail="Branch admins cannot grant church-wide access")
    if changes.get("is_active") is True and not membership.is_active:
        enforce_limit(db, current_user.church, "users")

    # Never leave the church without a church-wide admin.
    was_wide_admin = membership.role == "church_admin" and membership.is_active and membership.branch_id is None
    will_be_wide_admin = (
        changes.get("role", membership.role) == "church_admin"
        and changes.get("is_active", membership.is_active)
        and (changes["branch_id"] if "branch_id" in changes else membership.branch_id) is None
    )
    if was_wide_admin and not will_be_wide_admin and _active_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="A church needs at least one church-wide admin")

    old = {"role": membership.role, "branch_id": str(membership.branch_id) if membership.branch_id else None,
           "is_active": membership.is_active}
    for field, value in changes.items():
        setattr(membership, field, value)
    record_audit(db, user_id=current_user.id, action="updated", table_name="memberships", record_id=membership.id,
                 old_value=old, new_value={k: str(v) if isinstance(v, UUID) else v for k, v in changes.items()})
    db.commit()
    db.refresh(membership)
    return {"status": "success", "data": _serialize(membership)}
