"""Pledge campaigns, pledges and pledge payments (tenant-scoped by the session)."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.donation import Donation, DonationFund
from app.models.member import Member
from app.models.outreach import Pledge, PledgeCampaign, PledgePayment
from app.schemas.outreach import CampaignCreate, CampaignUpdate, PledgeCreate, PledgePaymentCreate

ZERO = Decimal("0")


def _check_fund(db: Session, fund_id: UUID | None) -> None:
    if fund_id and db.query(DonationFund.id).filter(DonationFund.id == fund_id).first() is None:
        raise ValueError("Selected fund was not found")


def get_campaign(db: Session, campaign_id: UUID) -> PledgeCampaign | None:
    return db.query(PledgeCampaign).filter(PledgeCampaign.id == campaign_id).first()


def get_pledge(db: Session, pledge_id: UUID) -> Pledge | None:
    return db.query(Pledge).filter(Pledge.id == pledge_id).first()


def campaign_totals(db: Session, campaign_ids: list[UUID]) -> dict[UUID, dict]:
    if not campaign_ids:
        return {}
    pledged = dict(
        db.query(Pledge.campaign_id, func.coalesce(func.sum(Pledge.amount), 0))
        .filter(Pledge.campaign_id.in_(campaign_ids))
        .group_by(Pledge.campaign_id)
        .all()
    )
    counts = dict(
        db.query(Pledge.campaign_id, func.count(Pledge.id))
        .filter(Pledge.campaign_id.in_(campaign_ids))
        .group_by(Pledge.campaign_id)
        .all()
    )
    paid = dict(
        db.query(Pledge.campaign_id, func.coalesce(func.sum(PledgePayment.amount), 0))
        .join(PledgePayment, PledgePayment.pledge_id == Pledge.id)
        .filter(Pledge.campaign_id.in_(campaign_ids))
        .group_by(Pledge.campaign_id)
        .all()
    )
    return {
        cid: {
            "pledged_total": Decimal(pledged.get(cid, ZERO)),
            "paid_total": Decimal(paid.get(cid, ZERO)),
            "pledge_count": int(counts.get(cid, 0)),
        }
        for cid in campaign_ids
    }


def list_campaigns(db: Session, active_only: bool = False) -> list[PledgeCampaign]:
    query = db.query(PledgeCampaign)
    if active_only:
        query = query.filter(PledgeCampaign.is_active.is_(True))
    return query.order_by(PledgeCampaign.is_active.desc(), PledgeCampaign.start_date.desc()).all()


def create_campaign(db: Session, payload: CampaignCreate, created_by: UUID | None) -> PledgeCampaign:
    _check_fund(db, payload.fund_id)
    row = PledgeCampaign(**payload.model_dump(), created_by=created_by)
    db.add(row)
    db.flush()
    return row


def update_campaign(db: Session, row: PledgeCampaign, payload: CampaignUpdate) -> PledgeCampaign:
    data = payload.model_dump(exclude_unset=True)
    if "fund_id" in data:
        _check_fund(db, data["fund_id"])
    for field, value in data.items():
        setattr(row, field, value)
    if row.end_date and row.end_date < row.start_date:
        raise ValueError("end_date must be on or after start_date")
    db.flush()
    return row


def pledge_paid(pledge: Pledge) -> Decimal:
    return sum((Decimal(p.amount) for p in pledge.payments), ZERO)


def pledge_status(pledge: Pledge, paid: Decimal) -> str:
    if paid >= Decimal(pledge.amount):
        return "fulfilled"
    due = pledge.due_date or (pledge.campaign.end_date if pledge.campaign else None)
    if due and due < date.today():
        return "overdue"
    return "partial" if paid > 0 else "unpaid"


def create_pledge(db: Session, campaign: PledgeCampaign, payload: PledgeCreate) -> Pledge:
    if payload.member_id and db.query(Member.id).filter(Member.id == payload.member_id).first() is None:
        raise ValueError("Selected member was not found")
    row = Pledge(campaign_id=campaign.id, **payload.model_dump())
    db.add(row)
    db.flush()
    return row


def add_payment(db: Session, pledge: Pledge, payload: PledgePaymentCreate, recorded_by: UUID | None) -> PledgePayment:
    campaign = pledge.campaign
    donation_id = None
    if campaign.fund_id:
        donation = Donation(
            fund_id=campaign.fund_id,
            member_id=pledge.member_id,
            amount=payload.amount,
            donation_date=payload.paid_on,
            payment_method=payload.payment_method,
            reference=payload.reference,
            notes=f"Pledge payment: {campaign.name}",
            recorded_by=recorded_by,
        )
        db.add(donation)
        db.flush()
        donation_id = donation.id
    payment = PledgePayment(
        pledge_id=pledge.id,
        amount=payload.amount,
        paid_on=payload.paid_on,
        payment_method=payload.payment_method,
        reference=payload.reference,
        donation_id=donation_id,
        recorded_by=recorded_by,
    )
    db.add(payment)
    db.flush()
    db.refresh(pledge)
    return payment
