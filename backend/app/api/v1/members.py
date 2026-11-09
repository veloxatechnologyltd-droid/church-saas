from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.crud import attendance as attendance_crud
from app.crud import donation as donation_crud
from app.crud import member as member_crud
from app.db.database import get_db
from app.schemas.donation import DonationResponse
from app.schemas.member import MemberCreate, MemberResponse, MemberUpdate
from app.services.audit import record_audit

router = APIRouter()


def _serialize_member(member, low_attendance: bool = False) -> dict:
    row = MemberResponse.model_validate(member).model_dump()
    row["family_name"] = member.family.family_name if member.family else None
    row["low_attendance"] = low_attendance
    return row


def _serialize_donation_activity(row) -> dict:
    data = DonationResponse.model_validate(row).model_dump()
    data["fund_name"] = row.fund.name if row.fund else None
    data["batch_title"] = row.batch.title if row.batch else None
    data["member_name"] = f"{row.member.first_name} {row.member.last_name}" if row.member else None
    return data


@router.get("/")
def list_members(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    members, total = member_crud.get_members(db, skip=skip, limit=limit, search=search, status=status_filter)
    low_map = member_crud.build_low_attendance_map(db, [m.id for m in members])

    data = []
    for m in members:
        data.append(_serialize_member(m, low_map.get(m.id, False)))

    page = (skip // limit) + 1
    return {"status": "success", "data": data, "total": total, "page": page, "limit": limit}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    try:
        member = member_crud.create_member(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="members", record_id=member.id, new_value={"first_name": member.first_name, "last_name": member.last_name})
    db.commit()
    low_map = member_crud.build_low_attendance_map(db, [member.id])
    return {"status": "success", "data": _serialize_member(member, low_map.get(member.id, False))}


@router.get("/family/{family_id}")
def get_family_members(
    family_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    members = member_crud.get_members_by_family(db, family_id)
    low_map = member_crud.build_low_attendance_map(db, [m.id for m in members])

    data = []
    for m in members:
        data.append(_serialize_member(m, low_map.get(m.id, False)))

    return {"status": "success", "data": data}


@router.get("/export")
def export_members(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    members, _ = member_crud.get_members(db, skip=0, limit=100000)
    csv_data = member_crud.generate_members_csv(members)
    headers = {"Content-Disposition": "attachment; filename=members.csv"}
    return StreamingResponse(iter([csv_data]), media_type="text/csv", headers=headers)


@router.get("/{member_id}")
def get_member(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    member = member_crud.get_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    low_map = member_crud.build_low_attendance_map(db, [member.id])
    return {"status": "success", "data": _serialize_member(member, low_map.get(member.id, False))}


@router.get("/{member_id}/activity")
def get_member_activity(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    member = member_crud.get_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    overview = member_crud.get_member_activity_overview(db, member_id)
    attendance = attendance_crud.member_activity_summary(db, member_id)
    giving = donation_crud.member_giving_summary(db, member_id)

    return {
        "status": "success",
        "data": {
            "overview": overview,
            "attendance": attendance,
            "giving": {
                **giving,
                "recent_entries": [_serialize_donation_activity(row) for row in giving["recent_entries"]],
            },
        },
    }


@router.put("/{member_id}")
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    if payload.family_id and not member_crud.get_family(db, payload.family_id):
        raise HTTPException(status_code=400, detail="Selected family was not found")

    member = member_crud.update_member(db, member_id, payload)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    record_audit(db, user_id=current_user.id, action="updated", table_name="members", record_id=member.id, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    low_map = member_crud.build_low_attendance_map(db, [member.id])
    return {"status": "success", "data": _serialize_member(member, low_map.get(member.id, False))}


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    deleted = member_crud.soft_delete_member(db, member_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Member not found")
    record_audit(db, user_id=current_user.id, action="deactivated", table_name="members", record_id=member_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{member_id}/photo")
def upload_member_photo(
    member_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    member = member_crud.get_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    uploads_dir = Path("uploads/members")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    safe_filename = f"{member_id}_{uuid4().hex}{extension}"
    file_path = uploads_dir / safe_filename

    file_bytes = file.file.read()
    with open(file_path, "wb") as output:
        output.write(file_bytes)

    photo_url = f"/uploads/members/{safe_filename}"
    updated = member_crud.update_member(db, member_id, MemberUpdate(photo_url=photo_url))
    record_audit(db, user_id=current_user.id, action="updated", table_name="members", record_id=member_id, new_value={"photo_url": photo_url})
    db.commit()
    return {"status": "success", "data": _serialize_member(updated, member_crud.build_low_attendance_map(db, [member_id]).get(member_id, False))}
