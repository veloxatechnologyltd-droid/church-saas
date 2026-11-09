"""Behavioural tests for the tenancy constraints, against a real migrated Postgres.

Each rejection asserts the *name* of the constraint that fired (see ``rejected_by``).
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Church, Group, GroupMember, Membership
from tests.helpers import (
    make_branch, make_category, make_church, make_donation, make_expense, make_family, make_fund,
    make_group, make_group_member, make_member, make_membership, make_record, make_session,
    make_user, rejected_by,
)


# ---------------------------------------------------------------- churches

class TestChurches:
    def test_defaults(self, session):
        c = make_church(session, "grace-chapel")
        session.refresh(c)
        assert (c.status, c.plan, c.timezone, c.currency, c.settings) == ("trialing", "trial", "Africa/Accra", "GHS", {})

    def test_slug_is_globally_unique(self, session):
        make_church(session, "grace-chapel")
        with rejected_by(session, "uq_churches_slug"):
            make_church(session, "grace-chapel")

    @pytest.mark.parametrize("slug", ["Grace", "grace chapel", "grace_chapel", "-grace", "grace-", "grace--chapel", ""])
    def test_slug_format_is_enforced(self, session, slug):
        with rejected_by(session, "ck_churches_slug_format"):
            session.add(Church(name="X", slug=slug))

    def test_status_is_restricted(self, session):
        with rejected_by(session, "ck_churches_status"):
            session.add(Church(name="X", slug="x-church", status="banana"))

    def test_church_with_data_cannot_be_deleted(self, session):
        church = make_church(session)
        make_member(session, church)
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.delete(church)
                session.flush()


# ---------------------------------------------------------------- branches

class TestBranches:
    def test_each_church_can_have_its_own_main_branch(self, session):
        make_branch(session, make_church(session), is_main=True)
        make_branch(session, make_church(session), is_main=True)

    def test_only_one_main_branch_per_church(self, session):
        church = make_church(session)
        make_branch(session, church, "HQ", is_main=True)
        make_branch(session, church, "Annex", is_main=False)  # non-main branches are unlimited
        with rejected_by(session, "uq_branches_one_main_per_church"):
            make_branch(session, church, "Second HQ", is_main=True)

    def test_branch_name_is_unique_per_church_only(self, session):
        a, b = make_church(session), make_church(session)
        make_branch(session, a, "East")
        make_branch(session, b, "East")  # same name, other church: fine
        with rejected_by(session, "uq_branches_church_name"):
            make_branch(session, a, "East")


# ------------------------------------------------- per-church uniqueness

class TestPerChurchUniqueness:
    """The old global uniques (groups.name, funds name/code, categories name) are per church now."""

    def test_group_name(self, session):
        a, b = make_church(session), make_church(session)
        make_group(session, a, "Choir")
        make_group(session, b, "Choir")
        with rejected_by(session, "uq_groups_church_name"):
            make_group(session, a, "Choir")

    def test_fund_name_and_code(self, session):
        a, b = make_church(session), make_church(session)
        make_fund(session, a, "Tithe", "tithe")
        make_fund(session, b, "Tithe", "tithe")
        with rejected_by(session, "uq_donation_funds_church_name"):
            make_fund(session, a, "Tithe", "other")
        with rejected_by(session, "uq_donation_funds_church_code"):
            make_fund(session, a, "Other", "tithe")

    def test_fund_code_may_be_null_repeatedly(self, session):
        church = make_church(session)
        make_fund(session, church, "One", None)
        make_fund(session, church, "Two", None)

    def test_expense_category_name(self, session):
        a, b = make_church(session), make_church(session)
        make_category(session, a, "Utilities")
        make_category(session, b, "Utilities")
        with rejected_by(session, "uq_expense_categories_church_name"):
            make_category(session, a, "Utilities")

    def test_user_email_stays_globally_unique(self, session):
        make_user(session, "pastor@example.com")
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                make_user(session, "pastor@example.com")


# ------------------------------------------------------------ memberships

class TestMemberships:
    def test_user_can_belong_to_two_churches_with_different_roles(self, session):
        user = make_user(session)
        a, b = make_church(session), make_church(session)
        make_membership(session, a, user, "church_admin")
        make_membership(session, b, user, "finance")

    def test_one_membership_per_user_per_church(self, session):
        user, church = make_user(session), make_church(session)
        make_membership(session, church, user)
        with rejected_by(session, "uq_memberships_user_church"):
            make_membership(session, church, user, "secretary")

    @pytest.mark.parametrize("role", ["superadmin", "platform_admin", "admin", ""])
    def test_role_must_be_a_church_role(self, session, role):
        with rejected_by(session, "ck_memberships_role"):
            make_membership(session, make_church(session), make_user(session), role)

    def test_branch_scoped_membership_within_its_church(self, session):
        church = make_church(session)
        branch = make_branch(session, church)
        m = make_membership(session, church, make_user(session), "secretary", branch_id=branch.id)
        assert m.branch_id == branch.id

    def test_branch_from_another_church_is_rejected(self, session):
        a, b = make_church(session), make_church(session)
        foreign_branch = make_branch(session, b)
        with rejected_by(session, "fk_memberships_branch_id_same_church"):
            make_membership(session, a, make_user(session), branch_id=foreign_branch.id)

    def test_member_profile_is_per_church(self, session):
        user = make_user(session)
        a, b = make_church(session), make_church(session)
        profile_a, profile_b = make_member(session, a), make_member(session, b)
        make_membership(session, a, user, member_id=profile_a.id)
        make_membership(session, b, user, member_id=profile_b.id)

    def test_member_profile_from_another_church_is_rejected(self, session):
        a, b = make_church(session), make_church(session)
        foreign_member = make_member(session, b)
        with rejected_by(session, "fk_memberships_member_id_same_church"):
            make_membership(session, a, make_user(session), member_id=foreign_member.id)

    def test_deleting_a_user_removes_their_memberships(self, session):
        user, church = make_user(session), make_church(session)
        membership_id = make_membership(session, church, user).id
        session.delete(user)
        session.flush()
        session.expire_all()
        assert session.get(Membership, membership_id) is None


# --------------------------------------- same-church references (composite FKs)

class TestSameChurchReferences:
    """A row may only point at rows of its own church, enforced by the database itself."""

    @pytest.fixture()
    def two(self, session):
        return make_church(session), make_church(session)

    def test_donation_to_own_church_member_ok(self, session, two):
        a, _ = two
        make_donation(session, a, make_fund(session, a), member_id=make_member(session, a).id)

    def test_donation_cannot_reference_other_churchs_member(self, session, two):
        a, b = two
        with rejected_by(session, "fk_donations_member_id_same_church"):
            make_donation(session, a, make_fund(session, a), member_id=make_member(session, b).id)

    def test_donation_cannot_use_other_churchs_fund(self, session, two):
        a, b = two
        with rejected_by(session, "fk_donations_fund_id_same_church"):
            make_donation(session, a, make_fund(session, b))

    def test_donation_cannot_join_other_churchs_batch(self, session, two):
        from app.models import FinanceBatch
        from datetime import date
        a, b = two
        batch_b = FinanceBatch(church_id=b.id, title="Sun", service_date=date(2026, 1, 4))
        session.add(batch_b)
        session.flush()
        with rejected_by(session, "fk_donations_batch_id_same_church"):
            make_donation(session, a, make_fund(session, a), batch_id=batch_b.id)

    def test_donation_branch_must_be_same_church(self, session, two):
        a, b = two
        with rejected_by(session, "fk_donations_branch_id_same_church"):
            make_donation(session, a, make_fund(session, a), branch_id=make_branch(session, b).id)

    def test_null_optional_references_are_fine(self, session, two):
        a, _ = two
        d = make_donation(session, a, make_fund(session, a))  # no member, batch or branch
        assert d.member_id is None and d.branch_id is None

    def test_expense_cannot_use_other_churchs_category(self, session, two):
        a, b = two
        with rejected_by(session, "fk_expenses_category_id_same_church"):
            make_expense(session, a, make_category(session, b))

    def test_attendance_record_cannot_cross_churches(self, session, two):
        a, b = two
        sess_a, member_a = make_session(session, a), make_member(session, a)
        with rejected_by(session, "fk_attendance_records_member_id_same_church"):
            make_record(session, a, sess_a, make_member(session, b))
        with rejected_by(session, "fk_attendance_records_session_id_same_church"):
            make_record(session, a, make_session(session, b), member_a)

    def test_group_leader_must_be_same_church(self, session, two):
        a, b = two
        with rejected_by(session, "fk_groups_leader_id_same_church"):
            make_group(session, a, "Ushers", leader_id=make_member(session, b).id)

    def test_group_membership_cannot_cross_churches(self, session, two):
        a, b = two
        with rejected_by(session, "fk_group_members_member_id_same_church"):
            make_group_member(session, a, make_group(session, a), make_member(session, b))
        with rejected_by(session, "fk_group_members_group_id_same_church"):
            make_group_member(session, a, make_group(session, b, "Other"), make_member(session, a))

    def test_member_family_and_home_branch_must_be_same_church(self, session, two):
        a, b = two
        with rejected_by(session, "fk_members_family_id_same_church"):
            make_member(session, a, family_id=make_family(session, b).id)
        with rejected_by(session, "fk_members_home_branch_id_same_church"):
            make_member(session, a, home_branch_id=make_branch(session, b).id)

    def test_child_church_id_cannot_be_changed_to_orphan_it(self, session, two):
        """Moving a child to another church while keeping its parent reference must fail."""
        a, b = two
        d = make_donation(session, a, make_fund(session, a), member_id=make_member(session, a).id)
        with rejected_by(session, "fk_donations_"):
            d.church_id = b.id

    def test_cascade_delete_still_works_through_the_composite_fk(self, session, two):
        a, _ = two
        group, member = make_group(session, a), make_member(session, a)
        make_group_member(session, a, group, member)
        session.expire_all()
        session.query(Group).filter(Group.id == group.id).delete(synchronize_session=False)
        assert session.query(GroupMember).filter(GroupMember.group_id == group.id).count() == 0
