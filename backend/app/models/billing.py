"""Platform-side SaaS tables: plans, subscriptions, invoices, payments, billing events,
SMS credit ledger and the platform (operator) event log.

``plans`` and ``billing_events`` are platform data (no ``church_id``). Everything a
church owns carries ``church_id`` like any other tenant table.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique, same_church_fk


class Plan(Base):
    """A subscription plan. ``None`` in a limit column means unlimited."""

    __tablename__ = "plans"

    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price_monthly = Column(Numeric(12, 2), nullable=False, default=0)
    price_yearly = Column(Numeric(12, 2), nullable=True)
    currency = Column(String, nullable=False, default="GHS", server_default="GHS")
    max_members = Column(Integer, nullable=True)
    max_branches = Column(Integer, nullable=True)
    max_users = Column(Integer, nullable=True)
    monthly_sms_credits = Column(Integer, nullable=False, default=0, server_default="0")
    features = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    is_public = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")


class Subscription(ChurchScoped, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        id_church_unique("subscriptions"),
        CheckConstraint(
            "status IN ('trialing', 'active', 'past_due', 'canceled', 'expired')", name="ck_subscriptions_status"
        ),
        Index("ix_subscriptions_church_id", "church_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_code = Column(String, ForeignKey("plans.code"), nullable=False)
    status = Column(String, nullable=False, default="trialing")
    billing_cycle = Column(String, nullable=False, default="monthly", server_default="monthly")
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    provider = Column(String, nullable=True)
    provider_ref = Column(String, nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    plan = relationship("Plan")


class Invoice(ChurchScoped, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        id_church_unique("invoices"),
        CheckConstraint("status IN ('open', 'paid', 'void', 'failed')", name="ck_invoices_status"),
        CheckConstraint("kind IN ('subscription', 'sms_credits')", name="ck_invoices_kind"),
        Index("ix_invoices_church_created", "church_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number = Column(String, nullable=False, unique=True)
    kind = Column(String, nullable=False, default="subscription")
    description = Column(String, nullable=False)
    plan_code = Column(String, ForeignKey("plans.code"), nullable=True)
    sms_credits = Column(Integer, nullable=True)
    billing_cycle = Column(String, nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, nullable=False, default="GHS")
    status = Column(String, nullable=False, default="open")
    provider = Column(String, nullable=True)
    provider_ref = Column(String, nullable=True, index=True)
    checkout_url = Column(String, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Payment(ChurchScoped, Base):
    __tablename__ = "payments"
    __table_args__ = (
        same_church_fk("payments", "invoice_id", "invoices"),
        Index("ix_payments_church_created", "church_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, nullable=False, default="GHS")
    method = Column(String, nullable=True)  # momo, card, bank, manual
    provider = Column(String, nullable=True)
    provider_ref = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BillingEvent(Base):
    """Raw webhook log. ``(provider, event_id)`` is unique, which makes webhooks idempotent."""

    __tablename__ = "billing_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_billing_events_provider_event"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    event_id = Column(String, nullable=False)
    event_type = Column(String, nullable=True)
    payload = Column(JSONB, nullable=False)
    church_id = Column(UUID(as_uuid=True), ForeignKey("churches.id"), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SmsCreditEntry(ChurchScoped, Base):
    """Append-only ledger. ``churches.sms_credits`` is the running balance."""

    __tablename__ = "sms_credit_ledger"
    __table_args__ = (Index("ix_sms_credit_ledger_church_created", "church_id", "created_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delta = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)  # purchase, monthly_allowance, send, refund, grant
    reference = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Wall-clock (not transaction-start) time, so entries in one transaction keep their order.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(),
                        nullable=False)


class PlatformEvent(Base):
    """Operator actions (suspend, plan change, impersonation...). Not tenant data."""

    __tablename__ = "platform_events"
    __table_args__ = (Index("ix_platform_events_created", "created_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    church_id = Column(UUID(as_uuid=True), ForeignKey("churches.id", ondelete="CASCADE"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
