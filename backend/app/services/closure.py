"""Account closure and permanent data deletion (Ghana DPA: right to erasure).

1. ``close_church``: a church admin closes the account. Access stops immediately (the
   auth dependency rejects closed churches), the subscription is cancelled, and the data
   is kept for ``CLOSURE_RETENTION_DAYS`` so a mistake can be undone by support
   (``reopen_church``). The admin is expected to export their data first.
2. ``purge_church``: after the retention period the scheduled job deletes every
   tenant-owned row (ordered by foreign keys), the church's uploaded files, and any user
   left without a church. What survives, with no personal data: a minimal record (name, slug,
   dates, counts) in ``platform_events`` as proof of deletion, and the paid invoices in
   ``financial_archive`` (accounting/tax record-keeping) for ``FINANCIAL_RETENTION_YEARS``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import Base
from app.db.tenancy import clear_tenant
from app.models import (
    Church, FinancialArchive, Invoice, Membership, PasswordResetToken, Payment, PlatformEvent, Subscription, User,
)
from app.services import storage

logger = logging.getLogger("app.closure")


def close_church(db: Session, church: Church, *, actor_id: UUID | None, reason: str | None = None) -> Church:
    now = datetime.now(timezone.utc)
    church.settings = {**(church.settings or {}), "status_before_closed": church.status}
    church.status = "closed"
    church.closed_at = now
    church.purge_after = now + timedelta(days=settings.CLOSURE_RETENTION_DAYS)
    church.suspended_reason = None
    for subscription in db.query(Subscription).filter(
        Subscription.church_id == church.id, Subscription.status.in_(("trialing", "active", "past_due"))
    ):
        subscription.status = "canceled"
        subscription.canceled_at = now
    db.add(PlatformEvent(
        actor_user_id=actor_id, church_id=church.id, action="church_closed",
        details={"reason": reason, "purge_after": church.purge_after.isoformat()},
    ))
    return church


def reopen_church(db: Session, church: Church, *, actor_id: UUID | None) -> Church:
    """Undo a closure while the data still exists."""
    if church.status != "closed":
        raise ValueError("This church is not closed")
    if church.purge_after is not None and church.purge_after <= datetime.now(timezone.utc):
        raise ValueError("The retention period has ended; the data is due for deletion")
    previous = (church.settings or {}).get("status_before_closed") or "active"
    church.status = previous if previous in ("trialing", "active") else "active"
    church.closed_at = None
    church.purge_after = None
    db.add(PlatformEvent(actor_user_id=actor_id, church_id=church.id, action="church_reopened", details={}))
    return church


def purge_church(db: Session, church_id: UUID) -> dict:
    """Permanently delete one *closed* church and everything it owns. Caller commits."""
    clear_tenant(db)  # platform job: see every row (RLS lets an unset tenant through)
    church = db.query(Church).filter(Church.id == church_id).with_for_update().first()
    if church is None:
        raise ValueError("Church not found")
    if church.status != "closed":
        raise ValueError("Only a closed church can be purged")
    summary = {"church_name": church.name, "slug": church.slug,
               "closed_at": church.closed_at.isoformat() if church.closed_at else None}

    # Keep the accounting record of money received (no members, no personal data).
    summary["invoices_archived"] = _archive_paid_invoices(db, church)

    # Children before parents: reverse FK order over every table that has a church_id.
    deleted_rows = 0
    for table in reversed(Base.metadata.sorted_tables):
        if table.name == "churches" or "church_id" not in table.c:
            continue
        deleted_rows += db.execute(delete(table).where(table.c.church_id == church_id)).rowcount or 0
    summary["rows_deleted"] = deleted_rows

    # Users that belonged only to this church have nothing left: erase them too.
    # Platform admins are operators, not church data, so they stay.
    orphans = select(User.id).where(
        ~select(Membership.id).where(Membership.user_id == User.id).exists(),
        User.is_platform_admin.is_(False),
    )
    orphan_ids = list(db.execute(orphans).scalars())
    if orphan_ids:
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id.in_(orphan_ids)))
        db.execute(delete(User).where(User.id.in_(orphan_ids)))
    summary["users_deleted"] = len(orphan_ids)

    db.delete(church)
    db.flush()
    # church_id is gone; keep a minimal, non-personal proof that the deletion happened.
    db.add(PlatformEvent(church_id=None, action="church_purged", details=summary))
    storage.delete_church_files(church_id)  # best effort, after the rows are gone
    return summary


def _archive_paid_invoices(db: Session, church: Church) -> int:
    count = 0
    for invoice in db.query(Invoice).filter(Invoice.church_id == church.id, Invoice.status == "paid"):
        payments = db.query(Payment).filter(Payment.invoice_id == invoice.id, Payment.church_id == church.id).all()
        db.add(FinancialArchive(
            closed_church_id=church.id, church_name=church.name, church_slug=church.slug,
            invoice_number=invoice.number, kind=invoice.kind, description=invoice.description,
            plan_code=invoice.plan_code, sms_credits=invoice.sms_credits, amount=invoice.amount,
            currency=invoice.currency, provider=invoice.provider, provider_ref=invoice.provider_ref,
            paid_at=invoice.paid_at, invoice_created_at=invoice.created_at,
            payments=[{"amount": str(p.amount), "currency": p.currency, "method": p.method,
                       "provider": p.provider, "provider_ref": p.provider_ref,
                       "at": p.created_at.isoformat() if p.created_at else None} for p in payments],
        ))
        count += 1
    db.flush()
    return count


def purge_expired_archive(db: Session) -> int:
    """Delete archived invoices older than ``FINANCIAL_RETENTION_YEARS``."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * settings.FINANCIAL_RETENTION_YEARS)
    removed = db.execute(delete(FinancialArchive).where(FinancialArchive.archived_at < cutoff)).rowcount or 0
    db.commit()
    return removed


def purge_due(db: Session) -> list[dict]:
    """Purge every closed church whose retention period has ended (scheduled job)."""
    clear_tenant(db)
    now = datetime.now(timezone.utc)
    due = list(db.execute(
        select(Church.id).where(Church.status == "closed", Church.purge_after.is_not(None), Church.purge_after <= now)
    ).scalars())
    results = []
    for church_id in due:
        try:
            results.append(purge_church(db, church_id))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not purge church %s", church_id)
    purge_expired_archive(db)
    return results
