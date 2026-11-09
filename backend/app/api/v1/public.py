"""Public, unauthenticated endpoints, resolved by church slug or check-in code.

Every handler looks the church up first (no tenant bound yet), refuses churches that are
not trialing/active (404, so suspended churches are indistinguishable from unknown ones),
then calls ``bind_tenant`` so all later reads and writes are scoped to that church.
Bodies never carry a church id. Forms have a ``website`` honeypot: if a bot fills it we
answer exactly as on success and store nothing.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import prayer as prayer_crud
from app.crud import visitor as visitor_crud
from app.db.database import get_db
from app.db.tenancy import bind_tenant
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.church import Branch, Church
from app.models.member import Member
from app.schemas.outreach import PublicCheckin, PublicPrayerForm, PublicVisitorForm
from app.services.audit import record_audit

router = APIRouter()

OPEN_STATUSES = ("trialing", "active")
WELCOME_MESSAGE = "Thank you! We're so glad you visited. Someone from the church will be in touch soon."
PRAYER_MESSAGE = "Thank you. Your request has been received and our prayer team will be praying with you."


def _branding(church: Church) -> dict:
    return {
        "name": church.name,
        "slug": church.slug,
        "logo_url": church.logo_url,
        "primary_color": church.primary_color,
        "secondary_color": church.secondary_color,
        "address": church.address,
        "phone": church.phone,
        "website": church.website,
    }


def _open_church(db: Session, slug: str) -> Church:
    church = db.query(Church).filter(Church.slug == slug.strip().lower()).first()
    if church is None or church.status not in OPEN_STATUSES:
        raise HTTPException(status_code=404, detail="Church not found")
    return church


def _bind(db: Session, church: Church) -> None:
    main_branch_id = (
        db.query(Branch.id).filter(Branch.church_id == church.id, Branch.is_main.is_(True)).scalar()
    )
    bind_tenant(db, church.id, default_branch_id=main_branch_id)


@router.get("/churches/{slug}")
def church_branding(slug: str, db: Session = Depends(get_db)):
    return {"status": "success", "data": _branding(_open_church(db, slug))}


@router.post("/churches/{slug}/visitors", status_code=status.HTTP_201_CREATED)
def public_welcome_card(slug: str, form: PublicVisitorForm, db: Session = Depends(get_db)):
    church = _open_church(db, slug)
    if form.website:  # honeypot tripped
        return {"status": "success", "data": {"message": WELCOME_MESSAGE}}
    _bind(db, church)
    visitor, is_new = visitor_crud.record_public_visit(db, form)
    record_audit(db, user_id=None, action="created" if is_new else "returned", table_name="visitors",
                 record_id=visitor.id, new_value={"source": "public_form"})
    db.commit()
    return {"status": "success", "data": {"message": WELCOME_MESSAGE}}


@router.post("/churches/{slug}/prayer-requests", status_code=status.HTTP_201_CREATED)
def public_prayer_request(slug: str, form: PublicPrayerForm, db: Session = Depends(get_db)):
    church = _open_church(db, slug)
    if form.website:
        return {"status": "success", "data": {"message": PRAYER_MESSAGE}}
    _bind(db, church)
    row = prayer_crud.create_public_request(db, form)
    record_audit(db, user_id=None, action="created", table_name="prayer_requests", record_id=row.id,
                 new_value={"source": "public_form"})
    db.commit()
    return {"status": "success", "data": {"message": PRAYER_MESSAGE}}


def _open_checkin(db: Session, code: str) -> tuple[AttendanceSession, Church]:
    session = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.checkin_code == code, AttendanceSession.checkin_open.is_(True))
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="This check-in link is closed or does not exist")
    church = db.query(Church).filter(Church.id == session.church_id).first()
    if church is None or church.status not in OPEN_STATUSES:
        raise HTTPException(status_code=404, detail="This check-in link is closed or does not exist")
    return session, church


def _session_info(session: AttendanceSession) -> dict:
    return {
        "title": session.title,
        "session_date": session.session_date.isoformat(),
        "session_type": session.session_type,
    }


@router.get("/checkin/{code}")
def checkin_info(code: str, db: Session = Depends(get_db)):
    session, church = _open_checkin(db, code)
    return {"status": "success", "data": {"church": _branding(church), "session": _session_info(session), "open": True}}


@router.post("/checkin/{code}")
def self_checkin(code: str, payload: PublicCheckin, db: Session = Depends(get_db)):
    session, church = _open_checkin(db, code)
    _bind(db, church)

    predicate = visitor_crud.phone_matches(Member.phone, payload.phone)
    member = None
    if predicate is not None:
        # Prefer active members; ignore branch scoping (public users have no branch).
        member = (
            db.query(Member)
            .filter(predicate)
            .order_by((Member.membership_status == "active").desc(), Member.created_at)
            .first()
        )
    if member is None:
        return {"status": "success", "data": {"status": "not_found"}}

    record = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session.id, AttendanceRecord.member_id == member.id)
        .first()
    )
    if record is not None and record.status == "present":
        return {"status": "success", "data": {"status": "already_checked_in", "first_name": member.first_name}}

    now = datetime.now(timezone.utc)
    if record is None:
        db.add(AttendanceRecord(session_id=session.id, member_id=member.id, status="present",
                                checked_in_at=now, source="self_checkin"))
    else:
        record.status, record.checked_in_at, record.source = "present", now, "self_checkin"
    db.commit()
    return {"status": "success", "data": {"status": "checked_in", "first_name": member.first_name}}
