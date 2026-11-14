"""Creating a church (tenant): slug rules and the standard starting data."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.tenancy import bind_tenant
from app.models.billing import Subscription
from app.models.church import Branch, Church
from app.models.member import Member
from app.models.membership import Membership
from app.models.user import User
from app.services import sms_credits

RESERVED_SLUGS = {
    "admin", "api", "app", "www", "mail", "help", "support", "billing", "login", "signup", "register",
    "platform", "pricing", "settings", "dashboard", "public", "static", "assets", "docs", "blog", "status",
    "welcome", "pray", "checkin", "auth", "account", "accounts", "church", "churches", "ekklesia", "asafo", "root",
    "system", "test", "demo", "about", "terms", "privacy", "security", "dev", "staging", "health",
}
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:40].strip("-")


def slug_problem(slug: str) -> str | None:
    if not slug or len(slug) < 3:
        return "Use at least 3 characters"
    if len(slug) > 40:
        return "Use at most 40 characters"
    if not SLUG_RE.match(slug):
        return "Use lowercase letters, numbers and single hyphens"
    if slug in RESERVED_SLUGS:
        return "That address is reserved"
    return None


def slug_taken(db: Session, slug: str) -> bool:
    return db.query(Church.id).filter(Church.slug == slug).first() is not None


def suggest_slug(db: Session, base: str) -> str:
    base = slugify(base) or "church"
    if len(base) < 3:
        base = f"{base}-church"
    candidate = base
    while slug_problem(candidate) or slug_taken(db, candidate):
        candidate = f"{base[:33]}-{secrets.token_hex(2)}"
    return candidate


def create_church(
    db: Session,
    *,
    name: str,
    slug: str,
    user: User,
    first_name: str,
    last_name: str,
    phone: str | None = None,
    country: str = "GH",
    timezone_name: str = "Africa/Accra",
    currency: str = "GHS",
    denomination: str | None = None,
) -> tuple[Church, Membership]:
    """Create the tenant, its main branch, the admin's membership and member profile,
    standard funds/expense categories, a trial subscription and welcome SMS credits.

    Leaves ``db`` bound to the new church. Does not commit.
    """
    from app.crud.donation import STANDARD_EXPENSE_CATEGORIES, STANDARD_FUNDS
    from app.models.donation import DonationFund, ExpenseCategory

    now = datetime.now(timezone.utc)
    church = Church(
        name=name.strip(), slug=slug, status="trialing", plan=settings.TRIAL_PLAN,
        trial_ends_at=now + timedelta(days=settings.TRIAL_DAYS), country=country or "GH",
        timezone=timezone_name or "Africa/Accra", currency=currency or "GHS", phone=phone,
        email=user.email, denomination=denomination,
    )
    db.add(church)
    db.flush()

    branch = Branch(church_id=church.id, name="Main Branch", is_main=True)
    db.add(branch)
    db.flush()
    bind_tenant(db, church.id, default_branch_id=branch.id)

    member = Member(
        first_name=first_name.strip(), last_name=last_name.strip(), phone=phone, email=user.email,
        membership_status="active", date_joined=now.date(),
    )
    db.add(member)
    db.flush()
    membership = Membership(church_id=church.id, user_id=user.id, role="church_admin", member_id=member.id)
    db.add(membership)

    for item in STANDARD_FUNDS:
        db.add(DonationFund(**item))
    for item in STANDARD_EXPENSE_CATEGORIES:
        db.add(ExpenseCategory(**item))

    db.add(Subscription(
        church_id=church.id, plan_code=settings.TRIAL_PLAN, status="trialing",
        current_period_start=now, current_period_end=church.trial_ends_at,
    ))
    db.flush()
    if settings.SIGNUP_SMS_CREDITS:
        sms_credits.change_balance(db, church.id, settings.SIGNUP_SMS_CREDITS, "grant", reference="Welcome credits")
    return church, membership
