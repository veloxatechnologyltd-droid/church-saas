"""Small factories and an assertion helper for the DB-level tenancy tests."""
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    AttendanceRecord, AttendanceSession, Branch, Church, Donation, DonationFund, Expense,
    ExpenseCategory, Family, Group, GroupMember, Member, Membership, User,
)


@contextmanager
def rejected_by(db, constraint: str):
    """Assert the body is refused by the database, and by *this* named constraint.

    Matching the constraint name stops a test passing because of some unrelated error.
    """
    with pytest.raises(IntegrityError) as excinfo:
        with db.begin_nested():
            yield
            db.flush()
    assert constraint in str(excinfo.value.orig), (
        f"expected violation of {constraint!r}, got: {excinfo.value.orig}"
    )


def _flush(db, obj):
    db.add(obj)
    db.flush()
    return obj


def make_church(db, slug: str | None = None) -> Church:
    slug = slug or f"church-{uuid.uuid4().hex[:8]}"
    return _flush(db, Church(name=slug.replace("-", " ").title(), slug=slug))


def make_branch(db, church, name="Main", is_main=False) -> Branch:
    return _flush(db, Branch(church_id=church.id, name=name, is_main=is_main))


def make_user(db, email: str | None = None) -> User:
    # users.role is deprecated but still NOT NULL until the Phase 2 migration.
    return _flush(db, User(email=email or f"{uuid.uuid4().hex[:8]}@example.com", hashed_password="x", role="member"))


def make_member(db, church, first="Ama", last="Mensah", **kw) -> Member:
    return _flush(db, Member(church_id=church.id, first_name=first, last_name=last, **kw))


def make_family(db, church, name="Mensah") -> Family:
    return _flush(db, Family(church_id=church.id, family_name=name))


def make_group(db, church, name="Choir", **kw) -> Group:
    return _flush(db, Group(church_id=church.id, name=name, **kw))


def make_fund(db, church, name="Tithe", code=None) -> DonationFund:
    return _flush(db, DonationFund(church_id=church.id, name=name, code=code))


def make_category(db, church, name="Utilities") -> ExpenseCategory:
    return _flush(db, ExpenseCategory(church_id=church.id, name=name))


def make_donation(db, church, fund, **kw) -> Donation:
    return _flush(db, Donation(church_id=church.id, fund_id=fund.id, amount=10, donation_date=date(2026, 1, 4), **kw))


def make_expense(db, church, category, **kw) -> Expense:
    return _flush(db, Expense(church_id=church.id, category_id=category.id, amount=5, expense_date=date(2026, 1, 4), **kw))


def make_session(db, church, **kw) -> AttendanceSession:
    return _flush(db, AttendanceSession(church_id=church.id, title="Sunday", session_date=date(2026, 1, 4), **kw))


def make_record(db, church, session, member) -> AttendanceRecord:
    return _flush(db, AttendanceRecord(church_id=church.id, session_id=session.id, member_id=member.id, status="present"))


def make_group_member(db, church, group, member) -> GroupMember:
    return _flush(db, GroupMember(church_id=church.id, group_id=group.id, member_id=member.id))


def make_membership(db, church, user, role="church_admin", **kw) -> Membership:
    return _flush(db, Membership(church_id=church.id, user_id=user.id, role=role, **kw))


NOW = datetime(2026, 1, 4, 9, 0, tzinfo=timezone.utc)
