import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique, same_church_fk


class FinanceBatch(ChurchScoped, Base):
    __tablename__ = "finance_batches"
    __table_args__ = (
        id_church_unique("finance_batches"),
        same_church_fk("finance_batches", "branch_id", "branches"),
        Index("ix_finance_batches_church_date", "church_id", "service_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    service_date = Column(Date, nullable=False)
    service_type = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_closed = Column(Boolean, default=False, nullable=False)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    donations = relationship("Donation", back_populates="batch", foreign_keys="Donation.batch_id")


class ExpenseCategory(ChurchScoped, Base):
    __tablename__ = "expense_categories"
    __table_args__ = (
        id_church_unique("expense_categories"),
        UniqueConstraint("church_id", "name", name="uq_expense_categories_church_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    expenses = relationship("Expense", back_populates="category", foreign_keys="Expense.category_id")


class DonationFund(ChurchScoped, Base):
    __tablename__ = "donation_funds"
    __table_args__ = (
        id_church_unique("donation_funds"),
        UniqueConstraint("church_id", "name", name="uq_donation_funds_church_name"),
        UniqueConstraint("church_id", "code", name="uq_donation_funds_church_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    requires_member = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    donations = relationship("Donation", back_populates="fund", foreign_keys="Donation.fund_id")


class Donation(ChurchScoped, Base):
    __tablename__ = "donations"
    __table_args__ = (
        same_church_fk("donations", "member_id", "members"),
        same_church_fk("donations", "batch_id", "finance_batches"),
        same_church_fk("donations", "fund_id", "donation_funds"),
        same_church_fk("donations", "branch_id", "branches"),
        Index("ix_donations_church_date", "church_id", "donation_date"),
        Index("ix_donations_church_member", "church_id", "member_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), nullable=True)
    batch_id = Column(UUID(as_uuid=True), nullable=True)
    fund_id = Column(UUID(as_uuid=True), nullable=False)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    payment_method = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    donation_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    fund = relationship("DonationFund", back_populates="donations", foreign_keys=[fund_id])
    batch = relationship("FinanceBatch", back_populates="donations", foreign_keys=[batch_id])
    member = relationship("Member", foreign_keys=[member_id])


class Expense(ChurchScoped, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        same_church_fk("expenses", "category_id", "expense_categories"),
        same_church_fk("expenses", "branch_id", "branches"),
        Index("ix_expenses_church_date", "church_id", "expense_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), nullable=False)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    expense_date = Column(Date, nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    payment_method = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    vendor_name = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    category = relationship("ExpenseCategory", back_populates="expenses", foreign_keys=[category_id])
