"""Plans, subscription checkout, invoices, SMS credit top-ups and provider webhooks."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import CurrentUser, get_current_user, require_church_wide_admin, require_roles
from app.db.database import get_db
from app.models.billing import BillingEvent, Invoice, Plan, SmsCreditEntry
from app.services import billing as billing_service
from app.services.audit import record_audit
from app.services.plans import current_subscription, effective_plan, read_only_reason, serialize_plan, usage
from app.services.sms_credits import SMS_PACKS, get_pack

router = APIRouter()
sms_router = APIRouter()


class CheckoutRequest(BaseModel):
    plan_code: str
    billing_cycle: Literal["monthly", "yearly"] = "monthly"


class PackPurchase(BaseModel):
    pack_code: str


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    """Public: the pricing page uses it too."""
    plans = db.query(Plan).filter(Plan.is_public.is_(True)).order_by(Plan.sort_order).all()
    return {"status": "success", "data": [serialize_plan(p) for p in plans], "total": len(plans)}


@router.get("/subscription")
def get_subscription(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    church = current_user.church
    sub = current_subscription(db, church.id)
    plan = effective_plan(db, church)
    return {
        "status": "success",
        "data": {
            "plan": serialize_plan(plan) if plan else None,
            "plan_code": church.plan,
            "status": sub.status if sub else None,
            "billing_cycle": sub.billing_cycle if sub else None,
            "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
            "trial_ends_at": church.trial_ends_at.isoformat() if church.trial_ends_at else None,
            "church_status": church.status,
            "read_only_reason": read_only_reason(db, church),
            "provider": settings.BILLING_PROVIDER,
            "usage": usage(db, church.id),
        },
    }


@router.post("/checkout")
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_church_wide_admin),
):
    church = current_user.church
    plan = db.query(Plan).filter(Plan.code == payload.plan_code, Plan.is_public.is_(True)).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.code == "enterprise":
        raise HTTPException(status_code=400, detail="Contact us for Enterprise pricing")
    use = usage(db, church.id)
    for kind, field in (("members", "max_members"), ("branches", "max_branches"), ("users", "max_users")):
        limit = getattr(plan, field)
        if limit is not None and use[kind] > limit:
            raise HTTPException(
                status_code=400,
                detail=f"You have {use[kind]} {kind}, more than the {plan.name} plan allows ({limit}).",
            )

    if float(plan.price_monthly or 0) == 0:
        # Free plan: switch immediately, no payment.
        church.plan = plan.code
        church.status = "active"
        sub = current_subscription(db, church.id)
        if sub:
            sub.plan_code = plan.code
            sub.status = "active"
            sub.current_period_end = None
        record_audit(db, user_id=current_user.id, action="plan_changed", table_name="churches", record_id=church.id,
                     new_value={"plan": plan.code})
        db.commit()
        return {"status": "success", "data": {"invoice": None, "checkout_url": None, "plan_code": plan.code}}

    yearly = payload.billing_cycle == "yearly" and plan.price_yearly
    amount = plan.price_yearly if yearly else plan.price_monthly
    cycle = "yearly" if yearly else "monthly"
    invoice = billing_service.create_invoice(
        db, church, kind="subscription", description=f"{plan.name} plan ({cycle})", amount=amount,
        plan_code=plan.code, billing_cycle=cycle, user_id=current_user.id,
    )
    db.commit()
    db.refresh(invoice)
    return {"status": "success", "data": {"invoice": billing_service.serialize_invoice(invoice),
                                          "checkout_url": invoice.checkout_url}}


@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_church_wide_admin)):
    rows = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(100).all()
    return {"status": "success", "data": [billing_service.serialize_invoice(i) for i in rows], "total": len(rows)}


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: UUID, db: Session = Depends(get_db),
                current_user: CurrentUser = Depends(require_church_wide_admin)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"status": "success", "data": billing_service.serialize_invoice(invoice)}


@router.post("/cancel")
def cancel(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_church_wide_admin)):
    """Stop renewing. The church keeps its plan until the paid period ends, then becomes read-only."""
    from datetime import datetime, timezone

    sub = current_subscription(db, current_user.church_id)
    if sub is None or sub.status != "active":
        raise HTTPException(status_code=400, detail="There is no active paid subscription to cancel")
    sub.status = "canceled"
    sub.canceled_at = datetime.now(timezone.utc)
    record_audit(db, user_id=current_user.id, action="subscription_canceled", table_name="subscriptions",
                 record_id=sub.id)
    db.commit()
    return {"status": "success", "data": {"message": "Your plan will not renew. It stays active until the period ends."}}


@router.post("/fake/complete/{invoice_id}")
def fake_complete(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_church_wide_admin),
):
    """Development/demo only: simulates the provider confirming payment."""
    if settings.BILLING_PROVIDER != "fake":
        raise HTTPException(status_code=404, detail="Not found")
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status not in ("open", "paid"):
        raise HTTPException(status_code=400, detail="This invoice cannot be paid")
    applied = billing_service.apply_paid_invoice(db, invoice, method="momo")
    if applied:
        record_audit(db, user_id=current_user.id, action="invoice_paid", table_name="invoices", record_id=invoice.id,
                     new_value={"number": invoice.number, "amount": float(invoice.amount)})
    db.commit()
    db.refresh(invoice)
    return {"status": "success", "data": billing_service.serialize_invoice(invoice)}


@router.post("/webhooks/{provider}")
async def webhook(provider: str, request: Request, db: Session = Depends(get_db)):
    """Provider callback. Signature verified; ``(provider, event_id)`` is unique, so a
    replayed event is acknowledged without being applied twice."""
    impl = billing_service.get_provider()
    if provider != impl.name:
        raise HTTPException(status_code=404, detail="Unknown provider")
    body = await request.body()
    try:
        event = impl.verify_webhook(body, {k.lower(): v for k, v in request.headers.items()})
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook") from exc

    record = BillingEvent(provider=provider, event_id=event.event_id, event_type=event.event_type, payload=event.payload)
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "success", "data": {"duplicate": True}}

    invoice = None
    if event.provider_ref:
        invoice = db.query(Invoice).filter(Invoice.provider_ref == event.provider_ref).with_for_update().first()
    if invoice is not None:
        record.church_id = invoice.church_id
        if event.event_type == "payment.succeeded":
            # Never grant a plan/credits for a payment that does not match the invoice.
            if event.amount is None or event.amount != invoice.amount or not event.currency or event.currency != invoice.currency:
                record.error = f"Amount mismatch: got {event.amount} {event.currency}, invoice is {invoice.amount} {invoice.currency}"
            else:
                billing_service.apply_paid_invoice(db, invoice, provider_ref=event.provider_ref)
        elif event.event_type == "payment.failed" and invoice.status == "open":
            invoice.status = "failed"
    else:
        record.error = "No matching invoice"
    from datetime import datetime, timezone

    record.processed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "data": {"duplicate": False}}


# ------------------------------------------------------------------- SMS credits

@sms_router.get("")
def sms_balance(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    ledger = db.query(SmsCreditEntry).order_by(SmsCreditEntry.created_at.desc()).limit(50).all()
    return {
        "status": "success",
        "data": {
            "balance": current_user.church.sms_credits,
            "ledger": [
                {"id": str(e.id), "delta": e.delta, "balance_after": e.balance_after, "reason": e.reason,
                 "reference": e.reference, "created_at": e.created_at.isoformat() if e.created_at else None}
                for e in ledger
            ],
        },
    }


@sms_router.get("/packs")
def sms_packs():
    return {"status": "success", "data": SMS_PACKS, "total": len(SMS_PACKS)}


@sms_router.post("/purchase")
def purchase_pack(
    payload: PackPurchase,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_church_wide_admin),
):
    pack = get_pack(payload.pack_code)
    if pack is None:
        raise HTTPException(status_code=404, detail="SMS pack not found")
    invoice = billing_service.create_invoice(
        db, current_user.church, kind="sms_credits", description=f"{pack['credits']:,} SMS credits",
        amount=pack["price"], credits=pack["credits"], user_id=current_user.id,
    )
    db.commit()
    db.refresh(invoice)
    return {"status": "success", "data": {"invoice": billing_service.serialize_invoice(invoice),
                                          "checkout_url": invoice.checkout_url}}
