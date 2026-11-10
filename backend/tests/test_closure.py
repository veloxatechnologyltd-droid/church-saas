"""Account closure (admin-initiated, reversible) and permanent purge after retention."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.db.database import Base
from app.db.tenancy import clear_tenant
from app.models import Church, Member, Membership, PlatformEvent, Subscription, User
from app.services import closure
from tests.helpers import (
    DEFAULT_PASSWORD, make_category, make_donation, make_expense, make_family, make_fund, make_group,
    make_group_member, make_member, make_membership, make_record, make_session, make_user,
)
from tests.test_auth_api import bearer, login

PASSWORD = "very-secret-1"


@pytest.fixture(autouse=True)
def _config(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "console")
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "fake")


def _signup(client, name, email):
    r = client.post("/api/v1/signup", json={
        "church_name": name, "first_name": "Ad", "last_name": "Min", "email": email, "password": PASSWORD,
        "accept_terms": True,
    })
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    return {"headers": bearer(data["access_token"]), "church_id": data["active_church"]["id"], "email": email}


@pytest.fixture()
def grace(client):
    return _signup(client, "Grace Chapel Accra", "akosua@grace.test")


def _close(client, who, **overrides):
    body = {"password": PASSWORD, "confirm_slug": "grace-chapel-accra", **overrides}
    return client.post("/api/v1/church/close", json=body, headers=who["headers"])


class TestClose:
    def test_requires_slug_and_password(self, client, grace):
        assert _close(client, grace, confirm_slug="other").status_code == 400
        assert _close(client, grace, password="wrong-password").status_code == 400
        assert client.get("/api/v1/church", headers=grace["headers"]).status_code == 200  # still open

    def test_non_admin_cannot_close(self, client, session, grace):
        church = session.get(Church, grace["church_id"])
        user = make_user(session, "finance@grace.test")
        make_membership(session, church, user, role="finance")
        token = login(client, "finance@grace.test").json()["data"]["access_token"]
        r = client.post("/api/v1/church/close", json={"password": DEFAULT_PASSWORD, "confirm_slug": church.slug},
                        headers=bearer(token))
        assert r.status_code == 403

    def test_closing_blocks_access_and_schedules_the_purge(self, client, session, grace):
        r = _close(client, grace, reason="Merging with another church")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["retention_days"] == settings.CLOSURE_RETENTION_DAYS
        church = session.get(Church, grace["church_id"])
        session.refresh(church)
        assert church.status == "closed" and church.closed_at and church.purge_after > church.closed_at
        assert church.purge_after - church.closed_at == timedelta(days=settings.CLOSURE_RETENTION_DAYS)
        assert all(s.status in ("canceled", "expired") for s in session.query(Subscription).filter_by(church_id=church.id))
        assert client.get("/api/v1/church", headers=grace["headers"]).status_code == 401
        assert session.query(PlatformEvent).filter_by(action="church_closed", church_id=church.id).count() == 1

    def test_platform_admin_can_reopen_within_retention(self, client, session, grace):
        _close(client, grace)
        make_user(session, "ops@platform.test", is_platform_admin=True)
        ops = bearer(login(client, "ops@platform.test").json()["data"]["access_token"])
        r = client.post(f"/api/v1/platform/churches/{grace['church_id']}/reopen", headers=ops)
        assert r.status_code == 200 and r.json()["data"]["status"] == "trialing"
        assert client.get("/api/v1/church", headers=grace["headers"]).status_code == 200

    def test_cannot_reopen_after_retention(self, client, session, grace):
        _close(client, grace)
        church = session.get(Church, grace["church_id"])
        church.purge_after = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.flush()
        make_user(session, "ops@platform.test", is_platform_admin=True)
        ops = bearer(login(client, "ops@platform.test").json()["data"]["access_token"])
        assert client.post(f"/api/v1/platform/churches/{grace['church_id']}/reopen", headers=ops).status_code == 400

    def test_impersonating_support_cannot_close(self, client, session, grace):
        make_user(session, "ops@platform.test", is_platform_admin=True)
        ops = bearer(login(client, "ops@platform.test").json()["data"]["access_token"])
        token = client.post(f"/api/v1/platform/churches/{grace['church_id']}/impersonate", headers=ops).json()["data"]["access_token"]
        r = client.post("/api/v1/church/close", json={"password": DEFAULT_PASSWORD, "confirm_slug": "grace-chapel-accra"},
                        headers=bearer(token))
        assert r.status_code == 403


def _church_tables():
    return [t for t in Base.metadata.sorted_tables if "church_id" in t.c and t.name != "churches"]


def _count(session, table, church_id):
    return session.execute(select(text("count(*)")).select_from(table).where(table.c.church_id == church_id)).scalar()


class TestPurge:
    @pytest.fixture()
    def two_churches(self, client, session, grace):
        faith = _signup(client, "Faith Assembly", "kofi@faith.test")
        clear_tenant(session)  # the shared test session is still bound to the last request's church
        a = session.get(Church, grace["church_id"])
        # Rich data in A across many tables, and a user who belongs to both churches.
        fam, member = make_family(session, a), make_member(session, a, "Kwame", "Boateng")
        group, fund, cat = make_group(session, a), make_fund(session, a, "Special"), make_category(session, a, "Repairs")
        make_group_member(session, a, group, member)
        make_donation(session, a, fund)
        make_expense(session, a, cat)
        make_record(session, a, make_session(session, a), member)
        shared = make_user(session, "shared@both.test")
        make_membership(session, a, shared)
        make_membership(session, session.get(Church, faith["church_id"]), shared)
        make_user(session, "ops@platform.test", is_platform_admin=True)
        return grace, faith

    def _expire(self, session, church_id):
        church = session.get(Church, church_id)
        church.purge_after = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.flush()

    def test_purge_deletes_everything_of_a_closed_church_only(self, client, session, two_churches):
        grace, faith = two_churches
        before_b = {t.name: _count(session, t, faith["church_id"]) for t in _church_tables()}
        assert before_b["members"] >= 1
        assert _close(client, grace).status_code == 200
        self._expire(session, grace["church_id"])

        results = closure.purge_due(session)
        assert len(results) == 1 and results[0]["slug"] == "grace-chapel-accra" and results[0]["rows_deleted"] > 10

        # Church A: gone from every church-owned table.
        assert session.get(Church, grace["church_id"]) is None
        for table in _church_tables():
            assert _count(session, table, grace["church_id"]) == 0, table.name
        # Church B: untouched.
        assert {t.name: _count(session, t, faith["church_id"]) for t in _church_tables()} == before_b
        # Users: A-only admin erased; user in two churches, B's admin and the operator kept.
        emails = {u.email for u in session.query(User)}
        assert "akosua@grace.test" not in emails
        assert {"shared@both.test", "kofi@faith.test", "ops@platform.test"} <= emails
        assert session.query(Membership).filter_by(user_id=session.query(User.id).filter_by(email="shared@both.test").scalar()).count() == 1
        # Proof of deletion survives, without personal data.
        event = session.query(PlatformEvent).filter_by(action="church_purged").one()
        assert event.church_id is None and event.details["church_name"] == "Grace Chapel Accra"
        assert "akosua@grace.test" not in str(event.details)

    def test_not_due_and_not_closed_churches_are_left_alone(self, client, session, two_churches):
        grace, faith = two_churches
        _close(client, grace)  # closed, but still inside the retention period
        assert closure.purge_due(session) == []
        assert session.get(Church, grace["church_id"]) is not None
        with pytest.raises(ValueError):
            closure.purge_church(session, faith["church_id"])  # open churches can never be purged

    def test_purge_is_idempotent_through_the_cron_endpoint(self, client, session, two_churches, monkeypatch):
        grace, _ = two_churches
        monkeypatch.setattr(settings, "CRON_SECRET", "cron-secret")
        _close(client, grace)
        self._expire(session, grace["church_id"])
        headers = {"Authorization": "Bearer cron-secret"}
        assert client.get("/api/v1/internal/cron/purge-closed").status_code == 404  # needs the secret
        first = client.get("/api/v1/internal/cron/purge-closed", headers=headers).json()["data"]
        second = client.get("/api/v1/internal/cron/purge-closed", headers=headers).json()["data"]
        assert first["purged"] == 1 and second["purged"] == 0


class TestReadiness:
    def test_platform_admin_sees_checks_without_secrets(self, client, session, monkeypatch):
        monkeypatch.setattr(settings, "SENDGRID_API_KEY", "SG.super-secret")
        make_user(session, "ops@platform.test", is_platform_admin=True)
        ops = bearer(login(client, "ops@platform.test").json()["data"]["access_token"])
        r = client.get("/api/v1/platform/readiness", headers=ops)
        assert r.status_code == 200
        data = r.json()["data"]
        assert {c["key"] for c in data["checks"]} >= {"email", "sms", "billing", "storage", "cron"}
        assert "SG.super-secret" not in r.text

    def test_church_users_cannot_see_it(self, client, grace):
        assert client.get("/api/v1/platform/readiness", headers=grace["headers"]).status_code == 403


class TestTermsConsent:
    def test_signup_requires_acceptance_and_records_it(self, client, session):
        body = {"church_name": "No Terms Church", "first_name": "A", "last_name": "B",
                "email": "a@noterms.test", "password": PASSWORD}
        assert client.post("/api/v1/signup", json=body).status_code == 422
        assert client.post("/api/v1/signup", json={**body, "accept_terms": False}).status_code == 422
        r = client.post("/api/v1/signup", json={**body, "accept_terms": True})
        assert r.status_code == 201, r.text
        church = session.query(Church).filter_by(slug="no-terms-church").one()
        assert church.settings["terms_accepted"]["version"] == settings.LEGAL_VERSION


class TestClosedChurchStaysClosed:
    def test_invitation_to_a_closed_church_cannot_be_accepted(self, client, session, grace):
        r = client.post("/api/v1/invitations/", json={"email": "new@grace.test", "role": "secretary"}, headers=grace["headers"])
        assert r.status_code == 201, r.text
        from app.models import Invitation
        from app.crud import invitation as invitation_crud

        assert session.query(Invitation).filter_by(email="new@grace.test").count() == 1
        assert _close(client, grace).status_code == 200
        # The raw token only exists in the email; re-issue one directly for the test.
        church = session.get(Church, grace["church_id"])
        _, raw = invitation_crud.create_invitation(
            session, church_id=church.id, invited_by=None, email="late@grace.test", role="secretary",
            branch_id=None, member_id=None, expires_hours=24,
        )
        r = client.post("/api/v1/invitations/accept", json={"token": raw, "password": "very-secret-1"})
        assert r.status_code == 400
        assert session.query(User).filter_by(email="late@grace.test").count() == 0

    def test_a_late_payment_does_not_reopen_a_closed_church(self, client, session, grace):
        from app.models import Invoice
        from app.services import billing

        r = client.post("/api/v1/billing/checkout", json={"plan_code": "growth", "billing_cycle": "monthly"}, headers=grace["headers"])
        assert r.status_code in (200, 201), r.text
        invoice = session.query(Invoice).filter_by(church_id=grace["church_id"]).first()
        assert _close(client, grace).status_code == 200
        session.refresh(invoice)
        billing.apply_paid_invoice(session, invoice, method="manual")
        church = session.get(Church, grace["church_id"])
        session.refresh(church)
        assert church.status == "closed"


class TestFinancialArchive:
    def _paid_invoice(self, client, session, who):
        from app.models import Invoice
        from app.services import billing

        r = client.post("/api/v1/billing/checkout", json={"plan_code": "growth", "billing_cycle": "monthly"}, headers=who["headers"])
        assert r.status_code in (200, 201), r.text
        invoice = session.query(Invoice).filter_by(church_id=who["church_id"]).first()
        billing.apply_paid_invoice(session, invoice, method="manual")
        session.refresh(invoice)
        return invoice

    def test_paid_invoices_survive_the_purge_without_personal_data(self, client, session, grace):
        from app.models import FinancialArchive, Invoice, Payment

        invoice = self._paid_invoice(client, session, grace)
        number, amount = invoice.number, invoice.amount
        _close(client, grace)
        church = session.get(Church, grace["church_id"])
        church.purge_after = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.flush()
        clear_tenant(session)

        results = closure.purge_due(session)
        assert results[0]["invoices_archived"] == 1
        assert session.query(Invoice).filter_by(number=number).count() == 0
        assert session.query(Payment).count() == 0
        row = session.query(FinancialArchive).filter_by(invoice_number=number).one()
        assert row.amount == amount and row.church_name == "Grace Chapel Accra" and len(row.payments) == 1
        assert "akosua@grace.test" not in str(row.__dict__)

    def test_archive_is_deleted_after_the_retention_years(self, client, session, grace, monkeypatch):
        from app.models import FinancialArchive

        self._paid_invoice(client, session, grace)
        _close(client, grace)
        church = session.get(Church, grace["church_id"])
        church.purge_after = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.flush()
        clear_tenant(session)
        closure.purge_due(session)
        assert session.query(FinancialArchive).count() == 1
        monkeypatch.setattr(settings, "FINANCIAL_RETENTION_YEARS", 0)
        session.query(FinancialArchive).update({"archived_at": datetime.now(timezone.utc) - timedelta(days=1)})
        session.flush()
        assert closure.purge_expired_archive(session) == 1


class TestSecurityReviewFixes:
    """Regressions for the independent security review."""

    def _member_login(self, client, session, grace, role="member", branch=None, email="role@grace.test"):
        from app.models import Member

        church = session.get(Church, grace["church_id"])
        clear_tenant(session)
        user = make_user(session, email)
        member = make_member(session, church, "Plain", "Member")
        make_membership(session, church, user, role=role, member_id=member.id, branch_id=branch)
        token = login(client, email).json()["data"]["access_token"]
        return bearer(token), member

    def test_plain_member_cannot_read_the_congregation_or_money(self, client, session, grace):
        h, me = self._member_login(client, session, grace)
        for path in ("/api/v1/members/", "/api/v1/families/", "/api/v1/attendance/summary", "/api/v1/attendance/sessions",
                     "/api/v1/groups/", "/api/v1/donations/funds", "/api/v1/reports/donations/monthly",
                     "/api/v1/reports/members/growth", "/api/v1/communication/reminders", "/api/v1/audit/"):
            assert client.get(path, headers=h).status_code == 403, path
        dash = client.get("/api/v1/reports/dashboard", headers=h).json()["data"]
        assert set(dash) <= {"upcoming_events", "upcoming_event_list"}
        assert client.get(f"/api/v1/members/{me.id}", headers=h).status_code == 200  # own profile still works
        other = make_member(session, session.get(Church, grace["church_id"]), "Someone", "Else")
        assert client.get(f"/api/v1/members/{other.id}", headers=h).status_code == 403
        assert client.get(f"/api/v1/members/{other.id}/activity", headers=h).status_code == 403

    def test_group_leader_sees_no_money_on_the_dashboard(self, client, session, grace):
        h, _ = self._member_login(client, session, grace, role="group_leader", email="leader@grace.test")
        dash = client.get("/api/v1/reports/dashboard", headers=h).json()["data"]
        assert "donations_this_month" not in dash and "total_members" in dash
        assert client.get("/api/v1/reports/donations/monthly", headers=h).status_code == 403

    def test_branch_admin_cannot_do_church_wide_things(self, client, session, grace):
        from tests.helpers import make_branch

        church = session.get(Church, grace["church_id"])
        clear_tenant(session)
        branch = make_branch(session, church, "North")
        h, _ = self._member_login(client, session, grace, role="church_admin", branch=branch.id, email="branch@grace.test")
        assert client.put("/api/v1/church", json={"name": "Hijacked Name"}, headers=h).status_code == 403
        assert client.post("/api/v1/billing/checkout", json={"plan_code": "growth"}, headers=h).status_code == 403
        assert client.post("/api/v1/billing/cancel", headers=h).status_code == 403
        assert client.post("/api/v1/sms-credits/purchase", json={"pack_code": "sms_2000"}, headers=h).status_code == 403
        assert client.get("/api/v1/audit/", headers=h).status_code == 403
        assert client.post("/api/v1/branches", json={"name": "Rogue"}, headers=h).status_code == 403
        # The church-wide admin still can.
        assert client.put("/api/v1/church", json={"name": "Grace Chapel Renamed"}, headers=grace["headers"]).status_code == 200

    def test_support_session_cannot_plant_access_or_change_billing(self, client, session, grace):
        make_user(session, "ops@platform.test", is_platform_admin=True)
        ops = bearer(login(client, "ops@platform.test").json()["data"]["access_token"])
        imp = bearer(client.post(f"/api/v1/platform/churches/{grace['church_id']}/impersonate", headers=ops).json()["data"]["access_token"])
        assert client.post("/api/v1/invitations/", json={"email": "backdoor@evil.test", "role": "church_admin"}, headers=imp).status_code == 403
        assert client.post("/api/v1/billing/checkout", json={"plan_code": "growth"}, headers=imp).status_code == 403
        assert client.put("/api/v1/church", json={"name": "Support Edit"}, headers=imp).status_code == 403
        assert client.get("/api/v1/members/", headers=imp).status_code == 200  # support can still look

    def test_closing_a_church_kills_live_support_tokens(self, client, session, grace):
        make_user(session, "ops@platform.test", is_platform_admin=True)
        ops = bearer(login(client, "ops@platform.test").json()["data"]["access_token"])
        imp = bearer(client.post(f"/api/v1/platform/churches/{grace['church_id']}/impersonate", headers=ops).json()["data"]["access_token"])
        assert _close(client, grace).status_code == 200
        assert client.get("/api/v1/members/", headers=imp).status_code == 401

    def test_invitations_respect_the_user_limit_and_are_rate_limited(self, client, session, grace):
        church = session.get(Church, grace["church_id"])
        church.plan = "free"
        church.status = "active"
        session.flush()
        # free plan: 2 users. The owner is one; one invite fits, the next (pending) one does not.
        first = client.post("/api/v1/invitations/", json={"email": "one@grace.test", "role": "secretary"}, headers=grace["headers"])
        assert first.status_code == 201, first.text
        second = client.post("/api/v1/invitations/", json={"email": "two@grace.test", "role": "secretary"}, headers=grace["headers"])
        assert second.status_code == 402 and second.json()["detail"]["limit"] == "users"

    def test_purge_only_removes_the_purged_churchs_orphans(self, client, session, grace):
        from app.models import User as U

        _signup(client, "Faith Assembly", "kofi@faith.test")
        clear_tenant(session)
        stray = make_user(session, "stray@nowhere.test")  # a user with no church at all: not this purge's business
        _close(client, grace)
        church = session.get(Church, grace["church_id"])
        church.purge_after = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.flush()
        closure.purge_due(session)
        emails = {u.email for u in session.query(U)}
        assert "stray@nowhere.test" in emails and "akosua@grace.test" not in emails

    def test_environment_guard_fails_closed(self):
        import importlib

        import app.main as main

        for env in ("prod", "", "production-ish"):
            settings.ENVIRONMENT = env
            try:
                with pytest.raises(RuntimeError):
                    importlib.reload(main)
            finally:
                settings.ENVIRONMENT = "development"
        importlib.reload(main)

    def test_forwarded_for_uses_the_proxy_added_entry(self):
        from starlette.requests import Request

        from app.core.middleware import client_ip

        def req(xff):
            return Request({"type": "http", "headers": [(b"x-forwarded-for", xff.encode())], "client": ("9.9.9.9", 1)})

        assert client_ip(req("6.6.6.6, 203.0.113.7")) == "203.0.113.7"  # spoofed left entry ignored
        assert client_ip(req("203.0.113.7")) == "203.0.113.7"

    def test_login_is_throttled_per_account_across_ips(self, client):
        for i in range(10):
            r = client.post("/api/v1/auth/login", json={"email": "victim@grace.test", "password": "wrong-pass-1"},
                            headers={"X-Forwarded-For": f"10.0.0.{i}"})
            assert r.status_code == 401
        r = client.post("/api/v1/auth/login", json={"email": "victim@grace.test", "password": "wrong-pass-1"},
                        headers={"X-Forwarded-For": "10.0.0.99"})
        assert r.status_code == 429
