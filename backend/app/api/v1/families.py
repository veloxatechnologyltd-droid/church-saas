from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.crud import family as family_crud
from app.db.database import get_db
from app.schemas.family import FamilyCreate, FamilyResponse
from app.services.audit import record_audit

router = APIRouter()


def _serialize_family(family, member_count: int = 0) -> dict:
    return FamilyResponse(id=family.id, family_name=family.family_name, member_count=member_count).model_dump()


@router.get("/")
def list_families(
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = family_crud.list_families(db, search=search, limit=limit)
    return {"status": "success", "data": [_serialize_family(family, member_count) for family, member_count in rows], "total": len(rows)}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_family(
    payload: FamilyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    try:
        family = family_crud.create_family(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="families", record_id=family.id, new_value={"family_name": family.family_name})
    db.commit()
    return {"status": "success", "data": _serialize_family(family)}


@router.get("/{family_id}")
def get_family(
    family_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    family = family_crud.get_family(db, family_id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")
    return {"status": "success", "data": _serialize_family(family, member_count=len(family.members))}
