"""Outreach and care: first-time visitors, prayer requests and pledge campaigns."""
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique, same_church_fk

VISITOR_STATUSES = ("new", "contacted", "returning", "converted", "not_interested")
PRAYER_STATUSES = ("new", "praying", "answered", "closed")


class Visitor(ChurchScoped, Base):
    """A first-timer / guest. Captured by staff or via the church's public welcome form."""

    __tablename__ = "visitors"
    __table_args__ = (
        id_church_unique("visitors"),
        same_church_fk("visitors", "branch_id", "branches"),
        same_church_fk("visitors", "converted_member_id", "members"),
        CheckConstraint(
            "status IN ('new', 'contacted', 'returning', 'converted', 'not_interested')", name="ck_visitors_status"
        ),
        Index("ix_visitors_church_status", "church_id", "status"),
        Index("ix_visitors_church_visit_date", "church_id", "visit_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    age_group = Column(String, nullable=True)  # child, youth, adult, senior
    address = Column(Text, nullable=True)
    visit_date = Column(Date, nullable=False)
    how_heard = Column(String, nullable=True)
    invited_by = Column(String, nullable=True)
    prayer_request = Column(Text, nullable=True)
    wants_visit = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    interested_in_membership = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    status = Column(String, nullable=False, default="new", server_default="new")
    visit_count = Column(Integer, nullable=False, default=1, server_default="1")
    notes = Column(Text, nullable=True)
    source = Column(String, nullable=False, default="manual", server_default="manual")  # manual, form
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    converted_member_id = Column(UUID(as_uuid=True), nullable=True)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    assignee = relationship("User", foreign_keys=[assigned_to])
    converted_member = relationship("Member", foreign_keys=[converted_member_id])


class PrayerRequest(ChurchScoped, Base):
    __tablename__ = "prayer_requests"
    __table_args__ = (
        same_church_fk("prayer_requests", "member_id", "members", ondelete="SET NULL"),
        CheckConstraint("status IN ('new', 'praying', 'answered', 'closed')", name="ck_prayer_requests_status"),
        Index("ix_prayer_requests_church_status", "church_id", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), nullable=True)
    name = Column(String, nullable=True)  # NULL = anonymous
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    request = Column(Text, nullable=False)
    category = Column(String, nullable=True)  # healing, family, finances, salvation, thanksgiving, other
    is_confidential = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    status = Column(String, nullable=False, default="new", server_default="new")
    prayed_count = Column(Integer, nullable=False, default=0, server_default="0")
    response_notes = Column(Text, nullable=True)
    source = Column(String, nullable=False, default="manual", server_default="manual")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    member = relationship("Member", foreign_keys=[member_id])


class PledgeCampaign(ChurchScoped, Base):
    """A fundraising drive (building project, harvest, missions) with a target."""

    __tablename__ = "pledge_campaigns"
    __table_args__ = (
        id_church_unique("pledge_campaigns"),
        same_church_fk("pledge_campaigns", "fund_id", "donation_funds"),
        Index("ix_pledge_campaigns_church_active", "church_id", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    fund_id = Column(UUID(as_uuid=True), nullable=True)
    target_amount = Column(Numeric(14, 2), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    fund = relationship("DonationFund", foreign_keys=[fund_id])
    pledges = relationship("Pledge", back_populates="campaign", foreign_keys="Pledge.campaign_id")


class Pledge(ChurchScoped, Base):
    __tablename__ = "pledges"
    __table_args__ = (
        id_church_unique("pledges"),
        same_church_fk("pledges", "campaign_id", "pledge_campaigns", ondelete="CASCADE"),
        same_church_fk("pledges", "member_id", "members"),
        CheckConstraint("amount > 0", name="ck_pledges_amount_positive"),
        Index("ix_pledges_church_campaign", "church_id", "campaign_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), nullable=False)
    member_id = Column(UUID(as_uuid=True), nullable=True)
    pledger_name = Column(String, nullable=True)  # for non-members
    phone = Column(String, nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    due_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    campaign = relationship("PledgeCampaign", back_populates="pledges", foreign_keys=[campaign_id])
    member = relationship("Member", foreign_keys=[member_id])
    payments = relationship("PledgePayment", back_populates="pledge", foreign_keys="PledgePayment.pledge_id",
                            cascade="all, delete-orphan")


class PledgePayment(ChurchScoped, Base):
    __tablename__ = "pledge_payments"
    __table_args__ = (
        same_church_fk("pledge_payments", "pledge_id", "pledges", ondelete="CASCADE"),
        CheckConstraint("amount > 0", name="ck_pledge_payments_amount_positive"),
        Index("ix_pledge_payments_church_pledge", "church_id", "pledge_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pledge_id = Column(UUID(as_uuid=True), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    paid_on = Column(Date, nullable=False)
    payment_method = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    donation_id = Column(UUID(as_uuid=True), nullable=True)  # the matching finance entry, when a fund is linked
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pledge = relationship("Pledge", back_populates="payments", foreign_keys=[pledge_id])
