"""Pledge campaigns (building fund, harvest, missions...) and pledge tracking."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.crud import pledge as pledge_crud
from app.db.database import get_db
from app.schemas.outreach import CampaignCreate, CampaignUpdate, PledgeCreate, PledgePaymentCreate
from app.services.audit import record_audit

router = APIRouter()

ROLES = ("church_admin", "finance")


def _money(value) -> float:
    return float(value or 0)


def _serialize_campaign(campaign, totals: dict | None = None) -> dict:
    totals = totals or {"pledged_total": Decimal(0), "paid_total": Decimal(0), "pledge_count": 0}
    target = Decimal(campaign.target_amount) if campaign.target_amount else None
    basis = target or totals["pledged_total"]
    progress = round(float(totals["paid_total"] / basis * 100), 1) if basis else 0.0
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "description": campaign.description,
        "fund_id": str(campaign.fund_id) if campaign.fund_id else None,
        "fund_name": campaign.fund.name if campaign.fund else None,
        "target_amount": _money(target) if target is not None else None,
        "start_date": campaign.start_date.isoformat(),
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "is_active": campaign.is_active,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "pledged_total": _money(totals["pledged_total"]),
        "paid_total": _money(totals["paid_total"]),
        "pledge_count": totals["pledge_count"],
        "progress_pct": progress,
    }


def _serialize_pledge(pledge) -> dict:
    paid = pledge_crud.pledge_paid(pledge)
    member = pledge.member
    return {
        "id": str(pledge.id),
        "campaign_id": str(pledge.campaign_id),
        "member_id": str(pledge.member_id) if pledge.member_id else None,
        "member_name": f"{member.first_name} {member.last_name}".strip() if member else None,
        "pledger_name": pledge.pledger_name,
        "display_name": f"{member.first_name} {member.last_name}".strip() if member else pledge.pledger_name,
        "phone": pledge.phone or (member.phone if member else None),
        "amount": _money(pledge.amount),
        "paid": _money(paid),
        "balance": _money(max(Decimal(pledge.amount) - paid, Decimal(0))),
        "status": pledge_crud.pledge_status(pledge, paid),
        "due_date": pledge.due_date.isoformat() if pledge.due_date else None,
        "notes": pledge.notes,
        "created_at": pledge.created_at.isoformat() if pledge.created_at else None,
        "payments": [
            {
                "id": str(p.id),
                "amount": _money(p.amount),
                "paid_on": p.paid_on.isoformat(),
                "payment_method": p.payment_method,
                "reference": p.reference,
                "donation_id": str(p.donation_id) if p.donation_id else None,
            }
            for p in sorted(pledge.payments, key=lambda p: p.paid_on)
        ],
    }


def _campaign_or_404(db: Session, campaign_id: UUID):
    campaign = pledge_crud.get_campaign(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _pledge_or_404(db: Session, pledge_id: UUID):
    pledge = pledge_crud.get_pledge(db, pledge_id)
    if pledge is None:
        raise HTTPException(status_code=404, detail="Pledge not found")
    return pledge


@router.get("/campaigns")
def list_campaigns(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES)),
):
    campaigns = pledge_crud.list_campaigns(db, active_only=active_only)
    totals = pledge_crud.campaign_totals(db, [c.id for c in campaigns])
    return {"status": "success", "data": [_serialize_campaign(c, totals.get(c.id)) for c in campaigns],
            "total": len(campaigns)}


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES))):
    try:
        campaign = pledge_crud.create_campaign(db, payload, created_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="pledge_campaigns", record_id=campaign.id,
                 new_value={"name": campaign.name})
    db.commit()
    db.refresh(campaign)
    return {"status": "success", "data": _serialize_campaign(campaign)}


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES))):
    campaign = _campaign_or_404(db, campaign_id)
    totals = pledge_crud.campaign_totals(db, [campaign.id])
    data = _serialize_campaign(campaign, totals.get(campaign.id))
    data["pledges"] = [_serialize_pledge(p) for p in sorted(campaign.pledges, key=lambda p: p.created_at, reverse=True)]
    return {"status": "success", "data": data}


@router.put("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES)),
):
    campaign = _campaign_or_404(db, campaign_id)
    try:
        pledge_crud.update_campaign(db, campaign, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="updated", table_name="pledge_campaigns", record_id=campaign.id,
                 new_value=payload.model_dump(mode="json", exclude_unset=True))
    db.commit()
    db.refresh(campaign)
    totals = pledge_crud.campaign_totals(db, [campaign.id])
    return {"status": "success", "data": _serialize_campaign(campaign, totals.get(campaign.id))}


@router.post("/campaigns/{campaign_id}/pledges", status_code=status.HTTP_201_CREATED)
def create_pledge(
    campaign_id: UUID,
    payload: PledgeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES)),
):
    campaign = _campaign_or_404(db, campaign_id)
    try:
        pledge = pledge_crud.create_pledge(db, campaign, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="pledges", record_id=pledge.id,
                 new_value={"campaign_id": str(campaign.id), "amount": str(pledge.amount)})
    db.commit()
    db.refresh(pledge)
    return {"status": "success", "data": _serialize_pledge(pledge)}


@router.post("/{pledge_id}/payments", status_code=status.HTTP_201_CREATED)
def add_pledge_payment(
    pledge_id: UUID,
    payload: PledgePaymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES)),
):
    pledge = _pledge_or_404(db, pledge_id)
    payment = pledge_crud.add_payment(db, pledge, payload, recorded_by=current_user.id)
    record_audit(db, user_id=current_user.id, action="payment_recorded", table_name="pledges", record_id=pledge.id,
                 new_value={"amount": str(payment.amount), "paid_on": payment.paid_on.isoformat(),
                            "donation_id": str(payment.donation_id) if payment.donation_id else None})
    db.commit()
    db.refresh(pledge)
    return {"status": "success", "data": _serialize_pledge(pledge)}


@router.delete("/{pledge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pledge(pledge_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES))):
    pledge = _pledge_or_404(db, pledge_id)
    db.delete(pledge)
    record_audit(db, user_id=current_user.id, action="deleted", table_name="pledges", record_id=pledge_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
