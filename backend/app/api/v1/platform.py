"""Platform-admin (product owner) console API.

These endpoints run on a session with NO tenant bound (platform admins need not belong
to any church), so every query here filters by ``church_id`` explicitly. Every action
that changes a church is written to ``platform_events``.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.v1.auth import session_payload
from app.core.dependencies import CurrentUser, require_platform_admin
from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.billing import Invoice, Plan, PlatformEvent, SmsCreditEntry
from app.models.church import Church
from app.models.member import Member
from app.models.membership import Membership
from app.services import sms_credits
from app.services.audit import record_audit
from app.services.plans import current_subscription, serialize_plan, usage

router = APIRouter()


class SuspendRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class PlanChange(BaseModel):
    plan_code: str
    status: Optional[str] = Field(default=None, pattern="^(trialing|active)$")
    trial_ends_at: Optional[datetime] = None


class CreditGrant(BaseModel):
    credits: int = Field(ge=-100000, le=100000)
    reason: str = Field(default="grant", max_length=200)


def _event(db: Session, actor: CurrentUser, action: str, church_id: UUID | None = None, **details) -> None:
    db.add(PlatformEvent(actor_user_id=actor.id, church_id=church_id, action=action,
                         details={k: (str(v) if isinstance(v, (UUID, datetime)) else v) for k, v in details.items()}))


def _church(db: Session, church_id: UUID) -> Church:
    church = db.query(Church).filter(Church.id == church_id).first()
    if church is None:
        raise HTTPException(status_code=404, detail="Church not found")
    return church


@router.get("/stats")
def stats(db: Session = Depends(get_db), admin: CurrentUser = Depends(require_platform_admin)):
    now = datetime.now(timezone.utc)
    by_status = dict(db.query(Church.status, func.count(Church.id)).group_by(Church.status).all())
    by_plan = dict(
        db.query(Church.plan, func.count(Church.id)).filter(Church.status == "active").group_by(Church.plan).all()
    )
    prices = {p.code: float(p.price_monthly or 0) for p in db.query(Plan).all()}
    mrr = sum(prices.get(code, 0) * count for code, count in by_plan.items())
    revenue_30d = (
        db.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(Invoice.status == "paid", Invoice.paid_at >= now - timedelta(days=30))
        .scalar()
    )
    return {
        "status": "success",
        "data": {
            "churches_total": sum(by_status.values()),
            "by_status": by_status,
            "by_plan": by_plan,
            "members_total": db.query(func.count(Member.id)).scalar(),
            "users_total": db.query(func.count(func.distinct(Membership.user_id))).scalar(),
            "signups_last_30_days": db.query(func.count(Church.id)).filter(Church.created_at >= now - timedelta(days=30)).scalar(),
            "mrr": mrr,
            "revenue_last_30_days": float(revenue_30d or 0),
            "sms_sent_30d": int(
                db.query(func.coalesce(func.sum(-SmsCreditEntry.delta), 0))
                .filter(SmsCreditEntry.reason == "send", SmsCreditEntry.created_at >= now - timedelta(days=30))
                .scalar() or 0
            ),
        },
    }


@router.get("/churches")
def list_churches(
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_platform_admin),
):
    query = db.query(Church)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(or_(Church.name.ilike(like), Church.slug.ilike(like), Church.email.ilike(like)))
    if status_filter:
        query = query.filter(Church.status == status_filter)
    total = query.count()
    churches = query.order_by(Church.created_at.desc()).offset(skip).limit(limit).all()
    ids = [c.id for c in churches]
    members = dict(
        db.query(Member.church_id, func.count(Member.id))
        .filter(Member.church_id.in_(ids), func.coalesce(Member.membership_status, "active") != "inactive")
        .group_by(Member.church_id).all()
    )
    users = dict(
        db.query(Membership.church_id, func.count(Membership.id))
        .filter(Membership.church_id.in_(ids), Membership.is_active.is_(True))
        .group_by(Membership.church_id).all()
    )
    activity = dict(
        db.query(AuditLog.church_id, func.max(AuditLog.created_at)).filter(AuditLog.church_id.in_(ids))
        .group_by(AuditLog.church_id).all()
    )
    data = [{
        "id": str(c.id), "name": c.name, "slug": c.slug, "status": c.status, "plan": c.plan, "email": c.email,
        "phone": c.phone, "country": c.country,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "trial_ends_at": c.trial_ends_at.isoformat() if c.trial_ends_at else None,
        "member_count": members.get(c.id, 0), "user_count": users.get(c.id, 0), "sms_credits": c.sms_credits,
        "last_activity_at": activity[c.id].isoformat() if activity.get(c.id) else None,
    } for c in churches]
    return {"status": "success", "data": data, "total": total, "page": skip // limit + 1, "limit": limit}


@router.get("/churches/{church_id}")
def church_detail(church_id: UUID, db: Session = Depends(get_db),
                  admin: CurrentUser = Depends(require_platform_admin)):
    church = _church(db, church_id)
    sub = current_subscription(db, church.id)
    plan = db.query(Plan).filter(Plan.code == church.plan).first()
    admins = (
        db.query(Membership).filter(Membership.church_id == church.id, Membership.role == "church_admin",
                                    Membership.is_active.is_(True)).all()
    )
    events = (
        db.query(PlatformEvent).filter(PlatformEvent.church_id == church.id)
        .order_by(PlatformEvent.created_at.desc()).limit(20).all()
    )
    invoices = db.query(Invoice).filter(Invoice.church_id == church.id).order_by(Invoice.created_at.desc()).limit(10).all()
    from app.api.v1.church import serialize_church
    from app.services.billing import serialize_invoice

    return {
        "status": "success",
        "data": {
            "church": serialize_church(church),
            "plan": serialize_plan(plan) if plan else None,
            "subscription": {
                "status": sub.status, "plan_code": sub.plan_code,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            } if sub else None,
            "usage": usage(db, church.id),
            "admins": [m.user.email for m in admins if m.user],
            "invoices": [serialize_invoice(i) for i in invoices],
            "events": [{"action": e.action, "details": e.details,
                        "created_at": e.created_at.isoformat() if e.created_at else None} for e in events],
        },
    }


@router.post("/churches/{church_id}/suspend")
def suspend(church_id: UUID, payload: SuspendRequest, db: Session = Depends(get_db),
            admin: CurrentUser = Depends(require_platform_admin)):
    church = _church(db, church_id)
    if church.status == "closed":
        raise HTTPException(status_code=400, detail="This church is closed")
    previous = church.status
    church.status = "suspended"
    church.suspended_reason = payload.reason
    church.settings = {**(church.settings or {}), "status_before_suspension": previous}
    _event(db, admin, "church_suspended", church.id, reason=payload.reason, previous_status=previous)
    db.commit()
    return {"status": "success", "data": {"id": str(church.id), "status": church.status}}


@router.post("/churches/{church_id}/reactivate")
def reactivate(church_id: UUID, db: Session = Depends(get_db),
               admin: CurrentUser = Depends(require_platform_admin)):
    church = _church(db, church_id)
    if church.status != "suspended":
        raise HTTPException(status_code=400, detail="This church is not suspended")
    previous = (church.settings or {}).get("status_before_suspension") or "active"
    church.status = previous if previous in ("trialing", "active") else "active"
    church.suspended_reason = None
    _event(db, admin, "church_reactivated", church.id, status=church.status)
    db.commit()
    return {"status": "success", "data": {"id": str(church.id), "status": church.status}}


@router.put("/churches/{church_id}/plan")
def change_plan(church_id: UUID, payload: PlanChange, db: Session = Depends(get_db),
                admin: CurrentUser = Depends(require_platform_admin)):
    church = _church(db, church_id)
    plan = db.query(Plan).filter(Plan.code == payload.plan_code).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    old = {"plan": church.plan, "status": church.status}
    church.plan = plan.code
    if payload.status:
        church.status = payload.status
    if payload.trial_ends_at:
        church.trial_ends_at = payload.trial_ends_at
    sub = current_subscription(db, church.id)
    if sub:
        sub.plan_code = plan.code
        if payload.status == "active":
            sub.status = "active"
    _event(db, admin, "plan_changed", church.id, old=old, plan=plan.code, status=church.status,
           trial_ends_at=payload.trial_ends_at)
    db.commit()
    return {"status": "success", "data": {"id": str(church.id), "plan": church.plan, "status": church.status}}


@router.post("/churches/{church_id}/sms-credits")
def grant_credits(church_id: UUID, payload: CreditGrant, db: Session = Depends(get_db),
                  admin: CurrentUser = Depends(require_platform_admin)):
    church = _church(db, church_id)
    entry = sms_credits.change_balance(db, church.id, payload.credits, "grant", reference=payload.reason,
                                       user_id=admin.id)
    _event(db, admin, "sms_credits_granted", church.id, credits=payload.credits, reason=payload.reason)
    db.commit()
    return {"status": "success", "data": {"balance": entry.balance_after}}


@router.post("/churches/{church_id}/impersonate")
def impersonate(church_id: UUID, db: Session = Depends(get_db),
                admin: CurrentUser = Depends(require_platform_admin)):
    """Short-lived church_admin session for support. Recorded in the platform log AND in
    the church's own audit trail, so the church can see that support accessed it."""
    church = _church(db, church_id)
    if church.status == "closed":
        raise HTTPException(status_code=400, detail="This church is closed")
    membership = Membership(user_id=admin.id, church_id=church.id, role="church_admin")
    _event(db, admin, "impersonation_started", church.id, admin_email=admin.email)
    record_audit(db, church_id=church.id, user_id=admin.id, action="support_access", table_name="churches",
                 record_id=church.id, new_value={"by": admin.email})
    db.commit()
    return {"status": "success", "data": session_payload(db, admin.user, membership, church, impersonating=True)}


@router.post("/invoices/{invoice_id}/mark-paid")
def mark_invoice_paid(invoice_id: UUID, db: Session = Depends(get_db),
                      admin: CurrentUser = Depends(require_platform_admin)):
    """Confirm an offline (manual provider) payment and grant what the invoice bought."""
    from app.services.billing import apply_paid_invoice, serialize_invoice

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status not in ("open", "failed"):
        raise HTTPException(status_code=400, detail=f"Invoice is {invoice.status}")
    apply_paid_invoice(db, invoice, method="manual")
    _event(db, admin, "invoice_marked_paid", invoice.church_id, number=invoice.number, amount=float(invoice.amount))
    db.commit()
    db.refresh(invoice)
    return {"status": "success", "data": serialize_invoice(invoice)}


@router.get("/events")
def platform_events(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db),
                    admin: CurrentUser = Depends(require_platform_admin)):
    rows = db.query(PlatformEvent).order_by(PlatformEvent.created_at.desc()).limit(limit).all()
    names = dict(db.query(Church.id, Church.name).filter(Church.id.in_({r.church_id for r in rows if r.church_id})).all())
    return {
        "status": "success",
        "data": [{
            "id": str(r.id), "action": r.action, "church_id": str(r.church_id) if r.church_id else None,
            "church_name": names.get(r.church_id), "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows],
    }
