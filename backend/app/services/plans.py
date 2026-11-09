"""Plan limits, usage, and the church's account state (trial, read-only, suspended)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import Plan, SmsCreditEntry, Subscription
from app.models.church import Branch, Church
from app.models.member import Member
from app.models.membership import Membership

LIMIT_FIELDS = {
    "members": "max_members",
    "branches": "max_branches",
    "users": "max_users",
}


class PlanLimitError(HTTPException):
    def __init__(self, limit: str, message: str):
        super().__init__(status_code=402, detail={"code": "plan_limit", "limit": limit, "message": message})


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def effective_plan_code(church: Church) -> str:
    """During a trial the church gets the trial plan's limits."""
    if church.status == "trialing":
        return settings.TRIAL_PLAN
    return church.plan or "free"


def get_plan(db: Session, code: str) -> Plan | None:
    return db.query(Plan).filter(Plan.code == code).first()


def effective_plan(db: Session, church: Church) -> Plan | None:
    return get_plan(db, effective_plan_code(church)) or get_plan(db, "free")


def current_subscription(db: Session, church_id: UUID) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(Subscription.church_id == church_id)
        .order_by(Subscription.created_at.desc())
        .first()
    )


def read_only_reason(db: Session, church: Church) -> str | None:
    """Why this church may only read, or ``None`` when writes are allowed."""
    now = now_utc()
    if church.status == "trialing":
        if church.trial_ends_at is not None and church.trial_ends_at < now:
            return "Your free trial has ended. Choose a plan to keep adding and editing records."
        return None
    if church.status == "active":
        if church.plan == "free":
            return None
        sub = current_subscription(db, church.id)
        if sub and sub.current_period_end and sub.current_period_end + timedelta(days=settings.GRACE_DAYS) < now:
            return "Your subscription payment is overdue. Renew your plan to keep adding and editing records."
    return None


def usage(db: Session, church_id: UUID) -> dict:
    month_start = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    members = (
        db.query(func.count(Member.id))
        .filter(Member.church_id == church_id, func.coalesce(Member.membership_status, "active") != "inactive")
        .scalar()
    )
    branches = db.query(func.count(Branch.id)).filter(Branch.church_id == church_id, Branch.is_active.is_(True)).scalar()
    users = (
        db.query(func.count(Membership.id))
        .execution_options(skip_tenant_scope=True)
        .filter(Membership.church_id == church_id, Membership.is_active.is_(True))
        .scalar()
    )
    sms_sent = (
        db.query(func.coalesce(func.sum(-SmsCreditEntry.delta), 0))
        .filter(
            SmsCreditEntry.church_id == church_id,
            SmsCreditEntry.reason == "send",
            SmsCreditEntry.created_at >= month_start,
        )
        .scalar()
    )
    return {"members": int(members or 0), "branches": int(branches or 0), "users": int(users or 0),
            "sms_sent_this_month": int(sms_sent or 0)}


def plan_limits(plan: Plan | None) -> dict:
    if plan is None:
        return {"max_members": None, "max_branches": None, "max_users": None, "monthly_sms_credits": 0}
    return {
        "max_members": plan.max_members,
        "max_branches": plan.max_branches,
        "max_users": plan.max_users,
        "monthly_sms_credits": plan.monthly_sms_credits,
    }


def enforce_limit(db: Session, church: Church, kind: str, adding: int = 1) -> None:
    """Raise ``PlanLimitError`` if adding ``adding`` more ``kind`` would exceed the plan."""
    plan = effective_plan(db, church)
    limit = getattr(plan, LIMIT_FIELDS[kind], None) if plan else None
    if limit is None:
        return
    current = usage(db, church.id)[kind]
    if current + adding > limit:
        raise PlanLimitError(
            kind,
            f"Your {plan.name} plan allows up to {limit} {kind}. Upgrade your plan to add more.",
        )


def serialize_plan(plan: Plan) -> dict:
    return {
        "code": plan.code,
        "name": plan.name,
        "description": plan.description,
        "price_monthly": float(plan.price_monthly or 0),
        "price_yearly": float(plan.price_yearly) if plan.price_yearly is not None else None,
        "currency": plan.currency,
        "max_members": plan.max_members,
        "max_branches": plan.max_branches,
        "max_users": plan.max_users,
        "monthly_sms_credits": plan.monthly_sms_credits,
        "features": plan.features or [],
        "is_public": plan.is_public,
    }
