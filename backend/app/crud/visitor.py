"""Visitors (first-timers). Queries are tenant-scoped by the session (app/db/tenancy.py)."""
import re
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.outreach import Visitor
from app.schemas.outreach import PublicVisitorForm, VisitorCreate, VisitorUpdate

FOLLOW_UP_DAYS = 3  # a new visitor not contacted within this many days is overdue


def normalize_phone(raw: str | None) -> str | None:
    """Canonical local form: digits only, ``+233``/``233`` prefix == leading ``0``.

    ``024 123 4567``, ``+233 24 123 4567`` and ``233241234567`` all become ``0241234567``.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("233") and len(digits) == 12:
        digits = "0" + digits[3:]
    elif len(digits) == 9:
        digits = "0" + digits
    return digits or None


def phone_matches(column, raw: str | None):
    """SQL predicate: ``column`` holds the same phone number as ``raw`` (last 9 digits)."""
    canonical = normalize_phone(raw)
    if not canonical or len(canonical) < 7:
        return None
    return func.right(func.regexp_replace(column, r"\D", "", "g"), 9) == canonical[-9:]


def list_visitors(db: Session, status: str | None = None, search: str | None = None, skip: int = 0, limit: int = 20):
    query = db.query(Visitor)
    if status:
        query = query.filter(Visitor.status == status)
    if search:
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Visitor.first_name.ilike(keyword),
                Visitor.last_name.ilike(keyword),
                Visitor.phone.ilike(keyword),
                Visitor.email.ilike(keyword),
            )
        )
    total = query.count()
    rows = query.order_by(Visitor.visit_date.desc(), Visitor.created_at.desc()).offset(skip).limit(limit).all()
    return rows, total


def get_visitor(db: Session, visitor_id: UUID) -> Visitor | None:
    return db.query(Visitor).filter(Visitor.id == visitor_id).first()


def create_visitor(db: Session, payload: VisitorCreate, source: str = "manual") -> Visitor:
    data = payload.model_dump()
    data["visit_date"] = data.get("visit_date") or date.today()
    visitor = Visitor(**data, source=source)
    db.add(visitor)
    db.flush()
    return visitor


def record_public_visit(db: Session, form: PublicVisitorForm) -> tuple[Visitor, bool]:
    """Create a visitor from the welcome card, or count a return visit. Returns (visitor, is_new)."""
    existing = None
    predicate = phone_matches(Visitor.phone, form.phone)
    if predicate is not None:
        existing = db.query(Visitor).filter(predicate).order_by(Visitor.created_at.desc()).first()
    if existing is None and form.email:
        existing = (
            db.query(Visitor)
            .filter(func.lower(Visitor.email) == form.email.strip().lower())
            .order_by(Visitor.created_at.desc())
            .first()
        )
    if existing is not None:
        existing.visit_count = (existing.visit_count or 1) + 1
        existing.visit_date = form.visit_date or date.today()
        if existing.status not in ("converted", "not_interested"):
            existing.status = "returning"
        if form.prayer_request:
            existing.prayer_request = form.prayer_request
        existing.wants_visit = existing.wants_visit or form.wants_visit
        existing.interested_in_membership = existing.interested_in_membership or form.interested_in_membership
        db.flush()
        return existing, False

    data = form.model_dump(exclude={"website"})
    data["visit_date"] = data.get("visit_date") or date.today()
    visitor = Visitor(**data, source="form")
    db.add(visitor)
    db.flush()
    return visitor, True


def update_visitor(db: Session, visitor: Visitor, payload: VisitorUpdate) -> Visitor:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(visitor, field, value)
    db.flush()
    return visitor


def mark_contacted(db: Session, visitor: Visitor, notes: str | None) -> Visitor:
    visitor.last_contacted_at = datetime.now(timezone.utc)
    if visitor.status == "new":
        visitor.status = "contacted"
    if notes:
        stamp = date.today().isoformat()
        visitor.notes = f"{visitor.notes}\n[{stamp}] {notes}" if visitor.notes else f"[{stamp}] {notes}"
    db.flush()
    return visitor


def convert_to_member(db: Session, visitor: Visitor) -> Member:
    member = Member(
        first_name=visitor.first_name,
        last_name=visitor.last_name or "-",
        phone=visitor.phone,
        email=visitor.email,
        gender=visitor.gender,
        address=visitor.address,
        introduced_by=visitor.invited_by,
        date_joined=date.today(),
        membership_status="active",
        home_branch_id=visitor.branch_id,
    )
    db.add(member)
    db.flush()
    visitor.converted_member_id = member.id
    visitor.status = "converted"
    db.flush()
    return member


def visitor_summary(db: Session) -> dict:
    counts = dict(db.query(Visitor.status, func.count(Visitor.id)).group_by(Visitor.status).all())
    sources = dict(db.query(Visitor.source, func.count(Visitor.id)).group_by(Visitor.source).all())
    month_start = date.today().replace(day=1)
    this_month = db.query(func.count(Visitor.id)).filter(Visitor.visit_date >= month_start).scalar() or 0
    total = sum(counts.values())
    converted = counts.get("converted", 0)
    overdue = (
        db.query(func.count(Visitor.id))
        .filter(Visitor.status == "new", Visitor.visit_date <= date.today() - timedelta(days=FOLLOW_UP_DAYS))
        .scalar()
        or 0
    )
    return {
        "total": total,
        "new": counts.get("new", 0),
        "contacted": counts.get("contacted", 0),
        "returning": counts.get("returning", 0),
        "converted": converted,
        "not_interested": counts.get("not_interested", 0),
        "this_month": this_month,
        "conversion_rate": round(converted / total * 100, 1) if total else 0.0,
        "by_source": {"form": sources.get("form", 0), "manual": sources.get("manual", 0)},
        "follow_up_overdue": overdue,
    }
