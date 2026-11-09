"""Billing: a provider-agnostic interface plus the invoice/subscription bookkeeping.

``BillingProvider`` is what a payment provider must implement. Two exist:

* ``FakeProvider`` - for development, tests and demos. Its checkout URL is a frontend
  page whose "Pay" button calls ``POST /billing/fake/complete/{invoice_id}``.
* ``SeevplusProvider`` - **not implemented**: blocked until the owner supplies the
  Seevplus API documentation (SAAS_CHECKLIST Phase 7). Do not guess its endpoints.

Payments are applied by ``apply_paid_invoice`` only, whichever way they arrive
(fake completion or verified webhook), and it is idempotent.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import Invoice, Payment, Plan, Subscription
from app.models.church import Church
from app.services import sms_credits


@dataclass
class CheckoutSession:
    checkout_url: str
    provider_ref: str


@dataclass
class WebhookEvent:
    event_id: str
    event_type: str  # payment.succeeded | payment.failed | ...
    provider_ref: str | None
    payload: dict


class BillingProvider:
    name = "base"

    def create_checkout(self, invoice: Invoice, church: Church) -> CheckoutSession:  # pragma: no cover - interface
        raise NotImplementedError

    def verify_webhook(self, body: bytes, headers: dict) -> WebhookEvent:  # pragma: no cover - interface
        raise NotImplementedError

    def cancel(self, subscription: Subscription) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class FakeProvider(BillingProvider):
    """Deterministic provider. Webhooks are signed with HMAC-SHA256 of the raw body
    using ``BILLING_WEBHOOK_SECRET`` in header ``X-Signature``, the same scheme a real
    provider adapter should map onto."""

    name = "fake"

    def create_checkout(self, invoice: Invoice, church: Church) -> CheckoutSession:
        ref = f"fake_{secrets.token_hex(8)}"
        url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/billing/fake-checkout?invoice={invoice.id}"
        return CheckoutSession(checkout_url=url, provider_ref=ref)

    def verify_webhook(self, body: bytes, headers: dict) -> WebhookEvent:
        import json

        secret = settings.BILLING_WEBHOOK_SECRET
        signature = headers.get("x-signature", "")
        if not secret:
            raise ValueError("Webhook secret is not configured")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid webhook signature")
        data = json.loads(body or b"{}")
        return WebhookEvent(
            event_id=str(data["id"]), event_type=str(data.get("type", "")),
            provider_ref=data.get("provider_ref"), payload=data,
        )

    def cancel(self, subscription: Subscription) -> None:
        return None


class SeevplusProvider(BillingProvider):
    name = "seevplus"

    def __init__(self) -> None:
        raise NotImplementedError(
            "Seevplus is not implemented yet: waiting on the Seevplus API documentation (SAAS_CHECKLIST Phase 7)."
        )


def get_provider() -> BillingProvider:
    name = settings.BILLING_PROVIDER.strip().lower()
    if name == "fake":
        return FakeProvider()
    if name == "seevplus":
        return SeevplusProvider()
    raise RuntimeError(f"Unknown billing provider {settings.BILLING_PROVIDER!r}")


def _invoice_number(db: Session) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m")
    return f"INV-{stamp}-{secrets.token_hex(3).upper()}"


def create_invoice(
    db: Session,
    church: Church,
    *,
    kind: str,
    description: str,
    amount: Decimal | float,
    plan_code: str | None = None,
    billing_cycle: str | None = None,
    credits: int | None = None,
    user_id: UUID | None = None,
) -> Invoice:
    provider = get_provider()
    invoice = Invoice(
        church_id=church.id, number=_invoice_number(db), kind=kind, description=description,
        plan_code=plan_code, billing_cycle=billing_cycle, sms_credits=credits, amount=amount,
        currency=church.currency or "GHS", status="open", provider=provider.name, created_by=user_id,
    )
    db.add(invoice)
    db.flush()
    session = provider.create_checkout(invoice, church)
    invoice.checkout_url = session.checkout_url
    invoice.provider_ref = session.provider_ref
    return invoice


def apply_paid_invoice(db: Session, invoice: Invoice, method: str = "momo", provider_ref: str | None = None) -> bool:
    """Mark ``invoice`` paid and grant what it bought. Returns False if it was already paid."""
    if invoice.status == "paid":
        return False
    now = datetime.now(timezone.utc)
    invoice.status = "paid"
    invoice.paid_at = now
    db.add(Payment(
        church_id=invoice.church_id, invoice_id=invoice.id, amount=invoice.amount, currency=invoice.currency,
        method=method, provider=invoice.provider, provider_ref=provider_ref or invoice.provider_ref,
    ))
    church = db.query(Church).filter(Church.id == invoice.church_id).one()

    if invoice.kind == "sms_credits":
        sms_credits.change_balance(db, church.id, int(invoice.sms_credits or 0), "purchase", reference=invoice.number)
        return True

    plan = db.query(Plan).filter(Plan.code == invoice.plan_code).one()
    period = timedelta(days=365 if invoice.billing_cycle == "yearly" else 30)
    sub = (
        db.query(Subscription)
        .filter(Subscription.church_id == church.id)
        .order_by(Subscription.created_at.desc())
        .first()
    )
    # Renewing the same plan extends from the current period end; anything else starts now.
    start = now
    if sub and sub.plan_code == plan.code and sub.status == "active" and sub.current_period_end and sub.current_period_end > now:
        start = sub.current_period_end
    if sub is None:
        sub = Subscription(church_id=church.id, plan_code=plan.code)
        db.add(sub)
    sub.plan_code = plan.code
    sub.status = "active"
    sub.billing_cycle = invoice.billing_cycle or "monthly"
    sub.current_period_start = start
    sub.current_period_end = start + period
    sub.provider = invoice.provider
    sub.canceled_at = None
    church.plan = plan.code
    church.status = "active"
    church.suspended_reason = None
    # A paid plan includes a monthly SMS allowance; grant the first month now.
    if plan.monthly_sms_credits:
        sms_credits.change_balance(db, church.id, plan.monthly_sms_credits, "monthly_allowance", reference=invoice.number)
    return True


def serialize_invoice(invoice: Invoice) -> dict:
    return {
        "id": str(invoice.id),
        "number": invoice.number,
        "kind": invoice.kind,
        "description": invoice.description,
        "plan_code": invoice.plan_code,
        "billing_cycle": invoice.billing_cycle,
        "sms_credits": invoice.sms_credits,
        "amount": float(invoice.amount),
        "currency": invoice.currency,
        "status": invoice.status,
        "provider": invoice.provider,
        "checkout_url": invoice.checkout_url if invoice.status == "open" else None,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
    }
