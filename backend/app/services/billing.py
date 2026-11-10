"""Billing: a provider-agnostic interface plus the invoice/subscription bookkeeping.

``BillingProvider`` is what a payment provider must implement. Two exist:

* ``FakeProvider`` - for development, tests and demos. Its checkout URL is a frontend
  page whose "Pay" button calls ``POST /billing/fake/complete/{invoice_id}``.
* ``ManualProvider`` - offline MoMo/bank payment confirmed by a platform admin.
* ``SeevplusProvider`` - Seevplus (Seevcash) hosted checkout, API docs at
  https://docs.seevcash.com. Mobile money collection in GHS; signed webhooks.

Payments are applied by ``apply_paid_invoice`` only, whichever way they arrive
(fake completion or verified webhook), and it is idempotent.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import httpx
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
    # Amount in major units (e.g. 100 = GHS 100.00) when the provider reports one; the
    # webhook handler refuses to apply a payment that does not match the invoice.
    amount: Decimal | None = None
    currency: str | None = None


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


class ManualProvider(BillingProvider):
    """Production-safe until a payment API is integrated: the church gets an invoice with
    payment instructions (MoMo / bank transfer quoting the invoice number), and a platform
    admin marks it paid after confirming receipt (``POST /platform/invoices/{id}/mark-paid``)."""

    name = "manual"

    def create_checkout(self, invoice: Invoice, church: Church) -> CheckoutSession:
        url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/settings/billing?invoice={invoice.id}"
        return CheckoutSession(checkout_url=url, provider_ref=f"manual_{invoice.number}")

    def verify_webhook(self, body: bytes, headers: dict) -> WebhookEvent:
        raise ValueError("The manual provider has no webhooks")

    def cancel(self, subscription: Subscription) -> None:
        return None


class BillingProviderError(RuntimeError):
    """The provider rejected or failed a request (shown to the user as a 502)."""


class SeevplusProvider(BillingProvider):
    """Seevplus hosted checkout (mobile money, GHS).

    * ``create_checkout`` -> ``POST {base}/api/v1/developer/payments``; amounts are in the
      smallest unit (pesewas). The returned ``reference`` is stored as ``invoice.provider_ref``.
    * Webhooks (``payment.succeeded`` / ``payment.failed``) are signed:
      ``X-Seev-Signature: v1=hex(HMAC_SHA256(secret, f"{X-Seev-Timestamp}.{raw body}"))``.
      They are sent once with no retries, and abandoned checkouts send nothing.
    * Sandbox vs production is decided by the API key, not the URL.
    """

    name = "seevplus"
    TIMESTAMP_TOLERANCE_SECONDS = 300

    def __init__(self) -> None:
        if not settings.SEEVPLUS_API_KEY:
            raise RuntimeError("SEEVPLUS_API_KEY is not configured")

    def create_checkout(self, invoice: Invoice, church: Church) -> CheckoutSession:
        body = {
            "type": "checkout",
            "amount": int((Decimal(invoice.amount) * 100).to_integral_value()),
            "currency": invoice.currency,
            "recipient": {"name": church.name, "email": church.email or settings.SEEVPLUS_FALLBACK_EMAIL},
            "channels": ["mobile_money"],
            "redirect_url": f"{settings.FRONTEND_BASE_URL.rstrip('/')}/settings/billing?invoice={invoice.id}",
            "meta": {"invoiceId": str(invoice.id), "invoiceNumber": invoice.number, "churchId": str(church.id)},
        }
        if church.phone:
            body["recipient"]["phone"] = church.phone
        try:
            response = httpx.post(
                f"{settings.SEEVPLUS_BASE_URL.rstrip('/')}/api/v1/developer/payments",
                headers={
                    "Authorization": f"Bearer {settings.SEEVPLUS_API_KEY}",
                    "Idempotency-Key": f"invoice_{invoice.id}",  # one logical order = one key
                    "Content-Type": "application/json",
                },
                json=body, timeout=30.0,
            )
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BillingProviderError(f"Seevplus request failed: {exc}") from exc
        if response.status_code not in (200, 201) or not isinstance(payload.get("data"), dict):
            raise BillingProviderError(f"Seevplus rejected the checkout ({response.status_code}): {payload.get('message') or payload.get('error')}")
        data = payload["data"]
        if not data.get("checkout_url") or not data.get("reference"):
            raise BillingProviderError("Seevplus returned no checkout URL")
        return CheckoutSession(checkout_url=data["checkout_url"], provider_ref=data["reference"])

    def verify_webhook(self, body: bytes, headers: dict) -> WebhookEvent:
        secret = settings.BILLING_WEBHOOK_SECRET
        if not secret:
            raise ValueError("Webhook secret is not configured")
        timestamp = headers.get("x-seev-timestamp", "")
        signature = headers.get("x-seev-signature", "")
        try:
            age = abs(time.time() - float(timestamp))
        except ValueError as exc:
            raise ValueError("Invalid webhook timestamp") from exc
        if age > self.TIMESTAMP_TOLERANCE_SECONDS:
            raise ValueError("Webhook timestamp outside the allowed window")
        expected = "v1=" + hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected.encode(), signature.encode()):
            raise ValueError("Invalid webhook signature")

        data = json.loads(body or b"{}")
        transaction = (data.get("data") or {}).get("transaction") or {}
        reference = transaction.get("reference")
        if not reference:
            raise ValueError("Webhook has no transaction reference")
        # The envelope id changes on every replay, so dedupe on reference + status instead.
        event_id = f"{reference}:{transaction.get('status', '')}"
        try:
            amount = Decimal(str(transaction["amount"])) if transaction.get("amount") is not None else None
        except ArithmeticError:
            amount = None
        return WebhookEvent(
            event_id=event_id, event_type=str(data.get("event", "")), provider_ref=reference, payload=data,
            amount=amount, currency=(transaction.get("currency") or None),
        )

    def cancel(self, subscription: Subscription) -> None:
        # Seevplus has no recurring billing: each renewal is a new invoice the church pays.
        return None


def get_provider() -> BillingProvider:
    name = settings.BILLING_PROVIDER.strip().lower()
    if name == "fake":
        return FakeProvider()
    if name == "manual":
        return ManualProvider()
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
    try:
        session = provider.create_checkout(invoice, church)
    except BillingProviderError:
        db.delete(invoice)  # no checkout exists, so do not leave a dangling open invoice
        db.flush()
        raise
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
    # A payment never lifts a closure or an operator's suspension (e.g. a late webhook for a
    # closed church); the plan is still recorded so reopening restores what was paid for.
    if church.status not in ("closed", "suspended"):
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
        "payment_instructions": (
            settings.BILLING_MANUAL_INSTRUCTIONS.format(number=invoice.number, amount=f"{invoice.currency} {invoice.amount:,.2f}")
            if invoice.provider == "manual" and invoice.status == "open" else None
        ),
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
    }
