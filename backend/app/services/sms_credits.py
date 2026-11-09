"""Prepaid SMS credits: one credit = one SMS segment to one recipient.

``churches.sms_credits`` is the balance; every change appends a row to
``sms_credit_ledger``. Balance changes lock the church row (``FOR UPDATE``) so two
concurrent sends cannot both spend the same credits.
"""
from __future__ import annotations

import math
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.billing import SmsCreditEntry
from app.models.church import Church
from app.services.plans import PlanLimitError

# Credit packs a church can buy (GHS). Roughly 4-5 pesewas per SMS at volume.
SMS_PACKS = [
    {"code": "sms_500", "credits": 500, "price": 30.0, "currency": "GHS"},
    {"code": "sms_2000", "credits": 2000, "price": 100.0, "currency": "GHS"},
    {"code": "sms_5000", "credits": 5000, "price": 225.0, "currency": "GHS"},
    {"code": "sms_20000", "credits": 20000, "price": 800.0, "currency": "GHS"},
]


def get_pack(code: str) -> dict | None:
    return next((p for p in SMS_PACKS if p["code"] == code), None)


def segments(message: str) -> int:
    """GSM-7 segments: 160 chars in one SMS, 153 per part when concatenated.
    Non-GSM text (e.g. emoji) uses UCS-2: 70 / 67."""
    text = message or ""
    unicode = any(ord(ch) > 127 for ch in text)
    single, multi = (70, 67) if unicode else (160, 153)
    if len(text) <= single:
        return 1
    return math.ceil(len(text) / multi)


def credits_needed(message: str, recipients: int) -> int:
    return segments(message) * max(recipients, 0)


def _locked_church(db: Session, church_id: UUID) -> Church:
    return db.query(Church).filter(Church.id == church_id).with_for_update().one()


def ensure_balance(db: Session, church_id: UUID, needed: int) -> None:
    church = db.query(Church).filter(Church.id == church_id).one()
    if needed > (church.sms_credits or 0):
        raise PlanLimitError(
            "sms",
            f"This message needs {needed} SMS credits but your balance is {church.sms_credits}. "
            "Top up SMS credits in Settings -> SMS credits.",
        )


def change_balance(
    db: Session,
    church_id: UUID,
    delta: int,
    reason: str,
    reference: str | None = None,
    user_id: UUID | None = None,
    allow_negative: bool = False,
) -> SmsCreditEntry:
    """Apply ``delta`` and log it. Does not commit."""
    church = _locked_church(db, church_id)
    new_balance = (church.sms_credits or 0) + delta
    if new_balance < 0 and not allow_negative:
        raise PlanLimitError("sms", "Not enough SMS credits.")
    church.sms_credits = new_balance
    entry = SmsCreditEntry(
        church_id=church_id, delta=delta, balance_after=new_balance, reason=reason, reference=reference,
        created_by=user_id,
    )
    db.add(entry)
    return entry
