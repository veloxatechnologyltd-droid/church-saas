"""Prayer requests. Queries are tenant-scoped by the session (app/db/tenancy.py)."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.outreach import PrayerRequest
from app.schemas.outreach import PrayerRequestCreate, PrayerRequestUpdate, PublicPrayerForm


def list_requests(db: Session, status: str | None = None, skip: int = 0, limit: int = 20):
    query = db.query(PrayerRequest)
    if status:
        query = query.filter(PrayerRequest.status == status)
    total = query.count()
    rows = query.order_by(PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()
    return rows, total


def get_request(db: Session, request_id: UUID) -> PrayerRequest | None:
    return db.query(PrayerRequest).filter(PrayerRequest.id == request_id).first()


def create_request(db: Session, payload: PrayerRequestCreate, source: str = "manual") -> PrayerRequest:
    data = payload.model_dump()
    if payload.member_id:
        member = db.query(Member).filter(Member.id == payload.member_id).first()
        if member is None:
            raise ValueError("Selected member was not found")
        if not data.get("name"):
            data["name"] = f"{member.first_name} {member.last_name}".strip()
    row = PrayerRequest(**data, source=source)
    db.add(row)
    db.flush()
    return row


def create_public_request(db: Session, form: PublicPrayerForm) -> PrayerRequest:
    row = PrayerRequest(**form.model_dump(exclude={"website"}), source="form")
    db.add(row)
    db.flush()
    return row


def update_request(db: Session, row: PrayerRequest, payload: PrayerRequestUpdate) -> PrayerRequest:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.flush()
    return row


def mark_prayed(db: Session, row: PrayerRequest) -> PrayerRequest:
    row.prayed_count = (row.prayed_count or 0) + 1
    if row.status == "new":
        row.status = "praying"
    db.flush()
    return row
