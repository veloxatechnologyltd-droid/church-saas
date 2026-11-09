import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class FinanceBatch(Base):
    __tablename__ = "finance_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    service_date = Column(Date, nullable=False)
    service_type = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_closed = Column(Boolean, default=False, nullable=False)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    donations = relationship("Donation", back_populates="batch")


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    __table_args__ = (UniqueConstraint("name", name="uq_expense_categories_name"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    expenses = relationship("Expense", back_populates="category")


class DonationFund(Base):
    __tablename__ = "donation_funds"
    __table_args__ = (UniqueConstraint("name", name="uq_donation_funds_name"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True, unique=True)
    description = Column(Text, nullable=True)
    requires_member = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    donations = relationship("Donation", back_populates="fund")


class Donation(Base):
    __tablename__ = "donations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("members.id"), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("finance_batches.id"), nullable=True)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("donation_funds.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    payment_method = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    donation_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    fund = relationship("DonationFund", back_populates="donations")
    batch = relationship("FinanceBatch", back_populates="donations")
    member = relationship("Member")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    expense_date = Column(Date, nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    payment_method = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    vendor_name = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    category = relationship("ExpenseCategory", back_populates="expenses")
