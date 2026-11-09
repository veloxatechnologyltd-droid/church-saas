"""Schemas for outreach: visitors, prayer requests, pledge campaigns and public forms."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

VisitorStatus = Literal["new", "contacted", "returning", "converted", "not_interested"]
PrayerStatus = Literal["new", "praying", "answered", "closed"]
AgeGroup = Literal["child", "youth", "adult", "senior"]


# ------------------------------------------------------------------ visitors

class VisitorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: Optional[str] = Field(default=None, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=120)
    gender: Optional[str] = Field(default=None, max_length=20)
    age_group: Optional[AgeGroup] = None
    address: Optional[str] = Field(default=None, max_length=500)
    visit_date: Optional[date] = None
    how_heard: Optional[str] = Field(default=None, max_length=120)
    invited_by: Optional[str] = Field(default=None, max_length=120)
    prayer_request: Optional[str] = Field(default=None, max_length=2000)
    wants_visit: bool = False
    interested_in_membership: bool = False


class VisitorCreate(VisitorBase):
    notes: Optional[str] = Field(default=None, max_length=5000)
    assigned_to: Optional[UUID] = None


class VisitorUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    last_name: Optional[str] = Field(default=None, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=120)
    gender: Optional[str] = Field(default=None, max_length=20)
    age_group: Optional[AgeGroup] = None
    address: Optional[str] = Field(default=None, max_length=500)
    visit_date: Optional[date] = None
    how_heard: Optional[str] = Field(default=None, max_length=120)
    invited_by: Optional[str] = Field(default=None, max_length=120)
    prayer_request: Optional[str] = Field(default=None, max_length=2000)
    wants_visit: Optional[bool] = None
    interested_in_membership: Optional[bool] = None
    status: Optional[VisitorStatus] = None
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class VisitorContacted(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)


class VisitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    address: Optional[str] = None
    visit_date: date
    how_heard: Optional[str] = None
    invited_by: Optional[str] = None
    prayer_request: Optional[str] = None
    wants_visit: bool
    interested_in_membership: bool
    status: str
    visit_count: int
    notes: Optional[str] = None
    source: str
    branch_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    converted_member_id: Optional[UUID] = None
    last_contacted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PublicVisitorForm(VisitorBase):
    website: Optional[str] = Field(default=None, max_length=200)  # honeypot: humans leave it empty

    @model_validator(mode="after")
    def _needs_contact(self):
        if not (self.phone or "").strip() and not (self.email or "").strip():
            raise ValueError("Please give a phone number or an email address")
        return self


# ------------------------------------------------------------------ prayer requests

class PrayerRequestCreate(BaseModel):
    member_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=120)
    request: str = Field(min_length=3, max_length=4000)
    category: Optional[str] = Field(default=None, max_length=40)
    is_confidential: bool = False


class PrayerRequestUpdate(BaseModel):
    status: Optional[PrayerStatus] = None
    response_notes: Optional[str] = Field(default=None, max_length=4000)
    category: Optional[str] = Field(default=None, max_length=40)
    is_confidential: Optional[bool] = None


class PrayerRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: Optional[UUID] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    request: str
    category: Optional[str] = None
    is_confidential: bool
    status: str
    prayed_count: int
    response_notes: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime


class PublicPrayerForm(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=120)
    request: str = Field(min_length=3, max_length=4000)
    category: Optional[str] = Field(default=None, max_length=40)
    is_confidential: bool = False
    website: Optional[str] = Field(default=None, max_length=200)  # honeypot


# ------------------------------------------------------------------ pledges

class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    fund_id: Optional[UUID] = None
    target_amount: Optional[Decimal] = Field(default=None, gt=0)
    start_date: date
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    fund_id: Optional[UUID] = None
    target_amount: Optional[Decimal] = Field(default=None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class PledgeCreate(BaseModel):
    member_id: Optional[UUID] = None
    pledger_name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    amount: Decimal = Field(gt=0)
    due_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _who(self):
        if not self.member_id and not (self.pledger_name or "").strip():
            raise ValueError("Choose a member or enter the pledger's name")
        return self


class PledgePaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    paid_on: date
    payment_method: Optional[str] = Field(default=None, max_length=40)
    reference: Optional[str] = Field(default=None, max_length=120)


# ------------------------------------------------------------------ check-in

class CheckinToggle(BaseModel):
    open: bool


class PublicCheckin(BaseModel):
    phone: str = Field(min_length=6, max_length=30)
