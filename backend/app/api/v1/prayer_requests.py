"""Prayer requests for the pastoral team (also submitted publicly, see public.py)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.crud import prayer as prayer_crud
from app.db.database import get_db
from app.schemas.outreach import PrayerRequestCreate, PrayerRequestResponse, PrayerRequestUpdate
from app.services.audit import record_audit

router = APIRouter()

ROLES = ("church_admin", "secretary")


def _serialize(row) -> dict:
    return PrayerRequestResponse.model_validate(row).model_dump(mode="json")


def _get_or_404(db: Session, request_id: UUID):
    row = prayer_crud.get_request(db, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    return row


@router.get("/")
def list_prayer_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES)),
):
    rows, total = prayer_crud.list_requests(db, status=status_filter, skip=skip, limit=limit)
    return {"status": "success", "data": [_serialize(r) for r in rows], "total": total,
            "page": (skip // limit) + 1, "limit": limit}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_prayer_request(
    payload: PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES)),
):
    try:
        row = prayer_crud.create_request(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="prayer_requests", record_id=row.id)
    db.commit()
    db.refresh(row)
    return {"status": "success", "data": _serialize(row)}


@router.put("/{request_id}")
def update_prayer_request(
    request_id: UUID,
    payload: PrayerRequestUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES)),
):
    row = _get_or_404(db, request_id)
    prayer_crud.update_request(db, row, payload)
    record_audit(db, user_id=current_user.id, action="updated", table_name="prayer_requests", record_id=row.id,
                 new_value=payload.model_dump(mode="json", exclude_unset=True))
    db.commit()
    db.refresh(row)
    return {"status": "success", "data": _serialize(row)}


@router.post("/{request_id}/prayed")
def mark_prayed(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES))):
    row = _get_or_404(db, request_id)
    prayer_crud.mark_prayed(db, row)
    db.commit()
    db.refresh(row)
    return {"status": "success", "data": _serialize(row)}


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prayer_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES))):
    row = _get_or_404(db, request_id)
    db.delete(row)
    record_audit(db, user_id=current_user.id, action="deleted", table_name="prayer_requests", record_id=request_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
