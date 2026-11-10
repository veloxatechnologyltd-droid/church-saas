"""The active church: profile/branding settings, usage vs plan, onboarding, data export."""
import csv
import io
import re
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password
from app.core.dependencies import CurrentUser, get_current_user, require_roles
from app.db.database import get_db
from app.models.church import Church
from app.services import closure
from app.services.audit import record_audit
from app.services.plans import effective_plan, plan_limits, serialize_plan, usage
from app.services.storage import save_image

router = APIRouter()

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
SENDER_ID = re.compile(r"^[A-Za-z0-9 ]{3,11}$")


class ChurchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=120)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    timezone: Optional[str] = Field(default=None, max_length=64)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    denomination: Optional[str] = Field(default=None, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = Field(default=None, max_length=500)
    website: Optional[str] = Field(default=None, max_length=200)
    sms_sender_id: Optional[str] = None
    email_from: Optional[str] = Field(default=None, max_length=120)
    email_from_name: Optional[str] = Field(default=None, max_length=80)

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def _color(cls, value):
        if value in (None, ""):
            return None
        if not HEX_COLOR.match(value):
            raise ValueError("Use a hex colour like #1F4E79")
        return value.upper()

    @field_validator("sms_sender_id")
    @classmethod
    def _sender(cls, value):
        if value in (None, ""):
            return None
        if not SENDER_ID.match(value):
            raise ValueError("Sender ID: 3-11 letters, numbers or spaces")
        return value

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value):
        if value is None:
            return value
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError("Unknown timezone") from exc
        return value


def public_urls(church: Church) -> dict:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return {"welcome": f"{base}/welcome/{church.slug}", "prayer": f"{base}/pray/{church.slug}"}


def serialize_church(church: Church) -> dict:
    return {
        "id": str(church.id),
        "name": church.name,
        "slug": church.slug,
        "logo_url": church.logo_url,
        "primary_color": church.primary_color,
        "secondary_color": church.secondary_color,
        "timezone": church.timezone,
        "currency": church.currency,
        "country": church.country,
        "denomination": church.denomination,
        "phone": church.phone,
        "email": church.email,
        "address": church.address,
        "website": church.website,
        "sms_sender_id": church.sms_sender_id,
        "email_from": church.email_from,
        "email_from_name": church.email_from_name,
        "status": church.status,
        "closed_at": church.closed_at.isoformat() if church.closed_at else None,
        "purge_after": church.purge_after.isoformat() if church.purge_after else None,
        "plan": church.plan,
        "trial_ends_at": church.trial_ends_at.isoformat() if church.trial_ends_at else None,
        "sms_credits": church.sms_credits,
        "onboarding_completed_at": church.onboarding_completed_at.isoformat() if church.onboarding_completed_at else None,
        "created_at": church.created_at.isoformat() if church.created_at else None,
        "public_urls": public_urls(church),
    }


@router.get("")
def get_church(current_user: CurrentUser = Depends(get_current_user)):
    return {"status": "success", "data": serialize_church(current_user.church)}


@router.put("")
def update_church(
    payload: ChurchUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("church_admin")),
):
    church = current_user.church
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field in {"currency", "country"} and value:
            value = value.upper()
        setattr(church, field, value)
    record_audit(db, user_id=current_user.id, action="updated", table_name="churches", record_id=church.id,
                 new_value=changes)
    db.commit()
    db.refresh(church)
    return {"status": "success", "data": serialize_church(church)}


@router.post("/logo")
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("church_admin")),
):
    church = current_user.church
    church.logo_url = save_image(church.id, "branding", file)
    record_audit(db, user_id=current_user.id, action="updated", table_name="churches", record_id=church.id,
                 new_value={"logo_url": church.logo_url})
    db.commit()
    db.refresh(church)
    return {"status": "success", "data": serialize_church(church)}


@router.post("/onboarding/complete")
def complete_onboarding(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("church_admin")),
):
    church = current_user.church
    if church.onboarding_completed_at is None:
        church.onboarding_completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(church)
    return {"status": "success", "data": serialize_church(church)}


@router.get("/usage")
def church_usage(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    church = current_user.church
    plan = effective_plan(db, church)
    return {
        "status": "success",
        "data": {
            "plan": serialize_plan(plan) if plan else None,
            "status": church.status,
            "trial_ends_at": church.trial_ends_at.isoformat() if church.trial_ends_at else None,
            "usage": usage(db, church.id),
            "limits": plan_limits(plan),
            "sms_credits": church.sms_credits,
        },
    }


# ------------------------------------------------------------------ data export

def _rows_members(db: Session):
    from app.models.member import Member

    header = ["first_name", "last_name", "other_name", "gender", "date_of_birth", "phone", "email", "address",
              "occupation", "marital_status", "membership_status", "date_joined", "baptism_date"]
    rows = db.query(Member).order_by(Member.last_name, Member.first_name).all()
    return header, [[getattr(m, h) for h in header] for m in rows]


def _rows_donations(db: Session):
    from app.models.donation import Donation

    header = ["donation_date", "fund", "amount", "currency", "member", "payment_method", "reference", "notes"]
    rows = db.query(Donation).order_by(Donation.donation_date.desc()).all()
    return header, [[
        d.donation_date, d.fund.name if d.fund else "", float(d.amount), d.currency,
        f"{d.member.first_name} {d.member.last_name}" if d.member else "", d.payment_method, d.reference, d.notes,
    ] for d in rows]


def _rows_attendance(db: Session):
    from app.models.attendance import AttendanceRecord, AttendanceSession

    header = ["session_date", "session", "member", "status", "checked_in_at", "source"]
    rows = (
        db.query(AttendanceRecord)
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .order_by(AttendanceSession.session_date.desc())
        .all()
    )
    return header, [[
        r.session.session_date, r.session.title, f"{r.member.first_name} {r.member.last_name}" if r.member else "",
        r.status, r.checked_in_at, r.source,
    ] for r in rows]


def _rows_visitors(db: Session):
    from app.models.outreach import Visitor

    header = ["visit_date", "first_name", "last_name", "phone", "email", "how_heard", "invited_by", "status",
              "visit_count", "wants_visit", "interested_in_membership", "source"]
    rows = db.query(Visitor).order_by(Visitor.visit_date.desc()).all()
    return header, [[getattr(v, h) for h in header] for v in rows]


EXPORTS = {"members": _rows_members, "donations": _rows_donations, "attendance": _rows_attendance,
           "visitors": _rows_visitors}
EXPORT_ROLES = {"members": {"church_admin", "secretary"}, "donations": {"church_admin", "finance"},
                "attendance": {"church_admin", "secretary"}, "visitors": {"church_admin", "secretary"}}


def _cell(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return "" if value is None else value


@router.get("/export/{dataset}")
def export_dataset(
    dataset: str,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if dataset not in EXPORTS:
        raise HTTPException(status_code=404, detail="Unknown export")
    if current_user.role not in EXPORT_ROLES[dataset]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    header, rows = EXPORTS[dataset](db)
    stamp = date.today().isoformat()
    filename = f"{current_user.church.slug}-{dataset}-{stamp}.{format}"
    record_audit(db, user_id=current_user.id, action="exported", table_name=dataset, new_value={"format": format,
                 "rows": len(rows)})
    db.commit()

    if format == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = dataset.title()
        ws.append(header)
        for row in rows:
            ws.append([_cell(v) for v in row])
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return StreamingResponse(buffer, media_type=media,
                                 headers={"Content-Disposition": f"attachment; filename={filename}"})

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_cell(v) for v in row])
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


# ------------------------------------------------------------------ account closure
class CloseChurchRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    confirm_slug: str = Field(min_length=1, max_length=120)
    reason: Optional[str] = Field(default=None, max_length=500)


@router.post("/close")
def close_church(
    payload: CloseChurchRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("church_admin")),
):
    """Close this church's account. Access stops now; the data is deleted for good after
    ``CLOSURE_RETENTION_DAYS`` (support can reopen it until then). Export your data first.

    Deliberately hard to do by accident or from a stolen session: the admin must retype
    the church's slug and their own password, and support sessions cannot do it.
    """
    church = current_user.church
    if current_user.impersonating:
        raise HTTPException(status_code=403, detail="Support sessions cannot close a church")
    if current_user.is_branch_scoped:
        raise HTTPException(status_code=403, detail="Only a church-wide administrator can close the church")
    if payload.confirm_slug.strip().lower() != church.slug:
        raise HTTPException(status_code=400, detail="The church URL name does not match")
    if not verify_password(payload.password, current_user.user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    record_audit(db, user_id=current_user.id, action="closed", table_name="churches", record_id=church.id,
                 new_value={"reason": payload.reason})
    closure.close_church(db, church, actor_id=current_user.id, reason=payload.reason)
    db.commit()
    return {"status": "success", "data": {
        "status": church.status,
        "closed_at": church.closed_at.isoformat(),
        "purge_after": church.purge_after.isoformat(),
        "retention_days": settings.CLOSURE_RETENTION_DAYS,
    }}
