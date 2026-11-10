"""Branches (locations) of the active church."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, get_current_user, require_church_wide_admin, require_roles
from app.db.database import get_db
from app.models.church import Branch
from app.models.member import Member
from app.services.audit import record_audit
from app.services.plans import enforce_limit

router = APIRouter()


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    address: Optional[str] = Field(default=None, max_length=500)


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    address: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


def _serialize(branch: Branch, member_count: int = 0) -> dict:
    return {
        "id": str(branch.id), "name": branch.name, "address": branch.address, "is_main": branch.is_main,
        "is_active": branch.is_active, "member_count": member_count,
        "created_at": branch.created_at.isoformat() if branch.created_at else None,
    }


def _get(db: Session, branch_id: UUID) -> Branch:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


def _name_taken(db: Session, name: str, exclude: UUID | None = None) -> bool:
    query = db.query(Branch.id).filter(func.lower(Branch.name) == name.strip().lower())
    if exclude:
        query = query.filter(Branch.id != exclude)
    return query.first() is not None


@router.get("")
def list_branches(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    query = db.query(Branch)
    if current_user.branch_id:
        query = query.filter(Branch.id == current_user.branch_id)
    branches = query.order_by(Branch.is_main.desc(), Branch.name).all()
    counts = dict(
        db.query(Member.home_branch_id, func.count(Member.id))
        .filter(func.coalesce(Member.membership_status, "active") != "inactive")
        .group_by(Member.home_branch_id)
        .all()
    )
    data = [_serialize(b, counts.get(b.id, 0)) for b in branches]
    return {"status": "success", "data": data, "total": len(data)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_church_wide_admin),
):
    if current_user.branch_id:
        raise HTTPException(status_code=403, detail="Only church-wide admins can add branches")
    enforce_limit(db, current_user.church, "branches")
    if _name_taken(db, payload.name):
        raise HTTPException(status_code=409, detail="A branch with this name already exists")
    branch = Branch(name=payload.name.strip(), address=payload.address, is_main=False)
    db.add(branch)
    db.flush()
    record_audit(db, user_id=current_user.id, action="created", table_name="branches", record_id=branch.id,
                 new_value={"name": branch.name})
    db.commit()
    db.refresh(branch)
    return {"status": "success", "data": _serialize(branch)}


@router.put("/{branch_id}")
def update_branch(
    branch_id: UUID,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_church_wide_admin),
):
    branch = _get(db, branch_id)
    if current_user.branch_id and current_user.branch_id != branch.id:
        raise HTTPException(status_code=404, detail="Branch not found")
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and _name_taken(db, changes["name"], exclude=branch.id):
        raise HTTPException(status_code=409, detail="A branch with this name already exists")
    if changes.get("is_active") is False and branch.is_main:
        raise HTTPException(status_code=400, detail="The main branch cannot be deactivated")
    if changes.get("is_active") is True and not branch.is_active:
        enforce_limit(db, current_user.church, "branches")
    for field, value in changes.items():
        setattr(branch, field, value.strip() if isinstance(value, str) and field == "name" else value)
    record_audit(db, user_id=current_user.id, action="updated", table_name="branches", record_id=branch.id,
                 new_value=changes)
    db.commit()
    db.refresh(branch)
    return {"status": "success", "data": _serialize(branch)}


@router.post("/{branch_id}/make-main")
def make_main(
    branch_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_church_wide_admin),
):
    if current_user.branch_id:
        raise HTTPException(status_code=403, detail="Only church-wide admins can change the main branch")
    branch = _get(db, branch_id)
    if not branch.is_active:
        raise HTTPException(status_code=400, detail="Activate the branch first")
    for other in db.query(Branch).filter(Branch.is_main.is_(True), Branch.id != branch.id).all():
        other.is_main = False
    db.flush()  # the partial unique index allows one main branch per church
    branch.is_main = True
    record_audit(db, user_id=current_user.id, action="updated", table_name="branches", record_id=branch.id,
                 new_value={"is_main": True})
    db.commit()
    db.refresh(branch)
    return {"status": "success", "data": _serialize(branch)}


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_branch(
    branch_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_church_wide_admin),
):
    if current_user.branch_id:
        raise HTTPException(status_code=403, detail="Only church-wide admins can remove branches")
    branch = _get(db, branch_id)
    if branch.is_main:
        raise HTTPException(status_code=400, detail="The main branch cannot be removed")
    branch.is_active = False
    record_audit(db, user_id=current_user.id, action="deactivated", table_name="branches", record_id=branch.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
