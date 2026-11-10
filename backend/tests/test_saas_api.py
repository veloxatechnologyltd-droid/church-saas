"""SaaS flows through the real API: signup/onboarding, settings, branches, team, plan
limits, billing (fake provider), SMS credits, read-only and suspended states, platform
admin + impersonation, rate limiting, and branch-scoped visibility."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.models import AuditLog, Church, DonationFund, ExpenseCategory, Member, Membership, PlatformEvent, Visitor
from tests.helpers import make_branch, make_church, make_member, make_membership, make_user
from tests.test_auth_api import bearer, login

SIGNUP = {
    "church_name": "Grace Chapel Accra", "first_name": "Akosua", "last_name": "Owusu",
    "email": "akosua@grace.test", "password": "very-secret-1", "phone": "0244000000", "accept_terms": True,
}


@pytest.fixture(autouse=True)
def _console_sms(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "console")
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "fake")


def signup(client, **overrides):
    return client.post("/api/v1/signup", json={**SIGNUP, **overrides})


@pytest.fixture()
def owner(client):
    response = signup(client)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    return {"headers": bearer(data["access_token"]), "church": data["active_church"], "data": data}


class TestSignup:
    def test_creates_church_with_defaults(self, client, session, owner):
        church = session.query(Church).filter_by(slug="grace-chapel-accra").one()
        assert church.status == "trialing" and church.plan == "growth" and church.trial_ends_at
        assert church.sms_credits == settings.SIGNUP_SMS_CREDITS
        assert len(church.branches) == 1 and church.branches[0].is_main
        assert session.query(DonationFund).filter_by(church_id=church.id).count() >= 5
        assert session.query(ExpenseCategory).filter_by(church_id=church.id).count() >= 5
        membership = session.query(Membership).filter_by(church_id=church.id).one()
        assert membership.role == "church_admin" and membership.member_id
        assert owner["church"]["role"] == "church_admin" and owner["church"]["onboarding_completed"] is False
        assert client.get("/api/v1/members/", headers=owner["headers"]).json()["total"] == 1

    def test_slug_rules(self, client, owner):
        taken = client.get("/api/v1/signup/slug-available", params={"slug": "Grace Chapel Accra"}).json()["data"]
        assert taken["available"] is False and taken["suggestion"] != "grace-chapel-accra"
        reserved = client.get("/api/v1/signup/slug-available", params={"slug": "admin"}).json()["data"]
        assert reserved["available"] is False
        assert signup(client, email="x@y.test", slug="admin").status_code == 422
        assert signup(client, email="x@y.test", slug="grace-chapel-accra").status_code == 409

    def test_existing_email_needs_its_password(self, client, owner):
        assert signup(client, church_name="Second Church", password="wrong-password-9").status_code == 409
        second = signup(client, church_name="Second Church")
        assert second.status_code == 201
        assert len(second.json()["data"]["churches"]) == 2

    def test_honeypot(self, client):
        assert signup(client, website="spam").status_code == 400


class TestSettingsBranchesTeam:
    def test_update_branding_and_complete_onboarding(self, client, owner):
        h = owner["headers"]
        r = client.put("/api/v1/church", json={"primary_color": "#1f4e79", "sms_sender_id": "GraceAcc"}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["primary_color"] == "#1F4E79"
        assert client.put("/api/v1/church", json={"primary_color": "blue"}, headers=h).status_code == 422
        assert client.put("/api/v1/church", json={"sms_sender_id": "WayTooLongSender"}, headers=h).status_code == 422
        done = client.post("/api/v1/church/onboarding/complete", headers=h).json()["data"]
        assert done["onboarding_completed_at"] and done["public_urls"]["welcome"].endswith("/welcome/grace-chapel-accra")

    def test_branches_crud_and_limits(self, client, owner):
        h = owner["headers"]
        east = client.post("/api/v1/branches", json={"name": "East Legon"}, headers=h)
        assert east.status_code == 201
        assert client.post("/api/v1/branches", json={"name": "east legon"}, headers=h).status_code == 409
        assert client.post("/api/v1/branches", json={"name": "Tema"}, headers=h).status_code == 201
        # Growth (trial) allows 3 branches.
        limited = client.post("/api/v1/branches", json={"name": "Kumasi"}, headers=h)
        assert limited.status_code == 402 and limited.json()["detail"]["code"] == "plan_limit"
        branches = client.get("/api/v1/branches", headers=h).json()["data"]
        main = next(b for b in branches if b["is_main"])
        assert client.delete(f"/api/v1/branches/{main['id']}", headers=h).status_code == 400
        moved = client.post(f"/api/v1/branches/{east.json()['data']['id']}/make-main", headers=h)
        assert moved.status_code == 200 and moved.json()["data"]["is_main"]

    def test_team_keeps_one_admin(self, client, session, owner):
        h = owner["headers"]
        team = client.get("/api/v1/team", headers=h).json()["data"]
        assert len(team) == 1
        r = client.put(f"/api/v1/team/{team[0]['membership_id']}", json={"role": "member"}, headers=h)
        assert r.status_code == 400

    def test_export_csv_and_xlsx(self, client, owner):
        h = owner["headers"]
        csv = client.get("/api/v1/church/export/members", headers=h)
        assert csv.status_code == 200 and "Akosua" in csv.text
        xlsx = client.get("/api/v1/church/export/donations", params={"format": "xlsx"}, headers=h)
        assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"


class TestBillingAndCredits:
    def test_checkout_and_fake_payment_activates_plan(self, client, session, owner):
        h = owner["headers"]
        plans = client.get("/api/v1/billing/plans").json()["data"]
        assert {p["code"] for p in plans} >= {"free", "growth", "kingdom"}
        r = client.post("/api/v1/billing/checkout", json={"plan_code": "kingdom", "billing_cycle": "yearly"}, headers=h)
        assert r.status_code == 200, r.text
        invoice = r.json()["data"]["invoice"]
        assert invoice["amount"] == 4990 and "/billing/fake-checkout" in r.json()["data"]["checkout_url"]
        paid = client.post(f"/api/v1/billing/fake/complete/{invoice['id']}", headers=h)
        assert paid.json()["data"]["status"] == "paid"
        again = client.post(f"/api/v1/billing/fake/complete/{invoice['id']}", headers=h)  # idempotent
        assert again.status_code == 200
        sub = client.get("/api/v1/billing/subscription", headers=h).json()["data"]
        assert sub["plan_code"] == "kingdom" and sub["church_status"] == "active" and sub["status"] == "active"
        credits = client.get("/api/v1/sms-credits", headers=h).json()["data"]
        assert credits["balance"] == settings.SIGNUP_SMS_CREDITS + 2000  # one monthly allowance

    def test_sms_pack_purchase_and_send_spends_credits(self, client, session, owner):
        h = owner["headers"]
        r = client.post("/api/v1/sms-credits/purchase", json={"pack_code": "sms_500"}, headers=h).json()["data"]
        client.post(f"/api/v1/billing/fake/complete/{r['invoice']['id']}", headers=h)
        before = client.get("/api/v1/sms-credits", headers=h).json()["data"]["balance"]
        assert before == settings.SIGNUP_SMS_CREDITS + 500
        sent = client.post("/api/v1/communication/sms", json={"message": "Service at 9am", "audience_type": "all_members"},
                           headers=h)
        assert sent.status_code == 201, sent.text
        after = client.get("/api/v1/sms-credits", headers=h).json()["data"]
        assert after["balance"] == before - 1 and after["ledger"][0]["reason"] == "send"

    def test_insufficient_credits_blocks_send(self, client, session, owner):
        church = session.query(Church).filter_by(slug="grace-chapel-accra").one()
        church.sms_credits = 0
        session.flush()
        r = client.post("/api/v1/communication/sms", json={"message": "Hi", "audience_type": "all_members"},
                        headers=owner["headers"])
        assert r.status_code == 402 and r.json()["detail"]["limit"] == "sms"

    def test_webhook_signature_and_idempotency(self, client, session, owner, monkeypatch):
        monkeypatch.setattr(settings, "BILLING_WEBHOOK_SECRET", "whsec")
        h = owner["headers"]
        invoice = client.post("/api/v1/sms-credits/purchase", json={"pack_code": "sms_2000"}, headers=h).json()["data"]["invoice"]
        from app.models import Invoice

        row = session.get(Invoice, invoice["id"])
        ref = row.provider_ref
        no_amount = json.dumps({"id": "evt_0", "type": "payment.succeeded", "provider_ref": ref}).encode()
        sig0 = hmac.new(b"whsec", no_amount, hashlib.sha256).hexdigest()
        # A success event that does not state amount and currency never grants anything.
        client.post("/api/v1/billing/webhooks/fake", content=no_amount, headers={"X-Signature": sig0})
        assert client.get("/api/v1/sms-credits", headers=h).json()["data"]["balance"] == settings.SIGNUP_SMS_CREDITS
        body = json.dumps({"id": "evt_1", "type": "payment.succeeded", "provider_ref": ref,
                           "amount": float(row.amount), "currency": row.currency}).encode()
        sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
        bad = client.post("/api/v1/billing/webhooks/fake", content=body, headers={"X-Signature": "nope"})
        assert bad.status_code == 400
        ok = client.post("/api/v1/billing/webhooks/fake", content=body, headers={"X-Signature": sig})
        assert ok.json()["data"]["duplicate"] is False
        dup = client.post("/api/v1/billing/webhooks/fake", content=body, headers={"X-Signature": sig})
        assert dup.json()["data"]["duplicate"] is True
        assert client.get("/api/v1/sms-credits", headers=h).json()["data"]["balance"] == settings.SIGNUP_SMS_CREDITS + 2000


class TestAccountStates:
    def test_expired_trial_is_read_only_but_can_pay(self, client, session, owner):
        h = owner["headers"]
        church = session.query(Church).filter_by(slug="grace-chapel-accra").one()
        church.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
        session.flush()
        assert client.get("/api/v1/members/", headers=h).status_code == 200
        blocked = client.post("/api/v1/members/", json={"first_name": "A", "last_name": "B"}, headers=h)
        assert blocked.status_code == 402 and blocked.json()["detail"]["code"] == "subscription_required"
        assert client.post("/api/v1/billing/checkout", json={"plan_code": "growth"}, headers=h).status_code == 200

    def test_suspended_church_is_blocked(self, client, session, owner):
        church = session.query(Church).filter_by(slug="grace-chapel-accra").one()
        church.status = "suspended"
        church.suspended_reason = "Unpaid"
        session.flush()
        r = client.get("/api/v1/members/", headers=owner["headers"])
        assert r.status_code == 403 and r.json()["detail"]["code"] == "church_suspended"
        assert client.get("/api/v1/public/churches/grace-chapel-accra").status_code == 404

    def test_free_plan_member_limit(self, client, session, owner):
        h = owner["headers"]
        client.post("/api/v1/billing/checkout", json={"plan_code": "free"}, headers=h)
        church = session.query(Church).filter_by(slug="grace-chapel-accra").one()
        assert church.plan == "free" and church.status == "active"
        for i in range(74):
            session.add(Member(church_id=church.id, first_name=f"M{i}", last_name="X"))
        session.flush()
        r = client.post("/api/v1/members/", json={"first_name": "One", "last_name": "Toomany"}, headers=h)
        assert r.status_code == 402 and r.json()["detail"]["limit"] == "members"


class TestPlatformAdmin:
    @pytest.fixture()
    def operator(self, client, session):
        make_user(session, "ops@platform.test", is_platform_admin=True)
        return bearer(login(client, "ops@platform.test").json()["data"]["access_token"])

    def test_non_admin_forbidden(self, client, owner):
        assert client.get("/api/v1/platform/churches", headers=owner["headers"]).status_code == 403

    def test_console_flow(self, client, session, owner, operator):
        stats = client.get("/api/v1/platform/stats", headers=operator).json()["data"]
        assert stats["churches_total"] >= 1
        listed = client.get("/api/v1/platform/churches", params={"search": "grace"}, headers=operator).json()
        cid = listed["data"][0]["id"]
        assert listed["data"][0]["member_count"] == 1

        assert client.post(f"/api/v1/platform/churches/{cid}/suspend", json={"reason": "Abuse"}, headers=operator).status_code == 200
        assert client.get("/api/v1/members/", headers=owner["headers"]).status_code == 403
        assert client.post(f"/api/v1/platform/churches/{cid}/reactivate", headers=operator).json()["data"]["status"] == "trialing"
        assert client.get("/api/v1/members/", headers=owner["headers"]).status_code == 200

        plan = client.put(f"/api/v1/platform/churches/{cid}/plan", json={"plan_code": "kingdom", "status": "active"},
                          headers=operator)
        assert plan.json()["data"]["plan"] == "kingdom"
        grant = client.post(f"/api/v1/platform/churches/{cid}/sms-credits", json={"credits": 100, "reason": "Pilot"},
                            headers=operator)
        assert grant.json()["data"]["balance"] == settings.SIGNUP_SMS_CREDITS + 100

        imp = client.post(f"/api/v1/platform/churches/{cid}/impersonate", headers=operator)
        assert imp.status_code == 200 and imp.json()["data"]["impersonating"] is True
        imp_headers = bearer(imp.json()["data"]["access_token"])
        members = client.get("/api/v1/members/", headers=imp_headers)
        assert members.status_code == 200 and members.json()["total"] == 1
        assert client.get("/api/v1/platform/stats", headers=imp_headers).status_code == 403
        assert session.query(AuditLog).filter_by(action="support_access").count() == 1
        actions = {e.action for e in session.query(PlatformEvent).all()}
        assert {"church_suspended", "church_reactivated", "plan_changed", "sms_credits_granted",
                "impersonation_started"} <= actions

    def test_operator_platform_calls_unaffected_by_church_token(self, client, session, owner, operator):
        # An operator who is also a church member: platform queries still see every church.
        other = make_church(session, "other-one")
        make_branch(session, other, "Main", is_main=True)
        data = client.get("/api/v1/platform/churches", headers=operator).json()
        assert data["total"] >= 2


class TestBranchScopingAndMultiChurch:
    def test_branch_scoped_user_sees_only_their_branch(self, client, session):
        church = make_church(session, "multi-branch")
        main = make_branch(session, church, "Main", is_main=True)
        east = make_branch(session, church, "East")
        make_member(session, church, "Main", "Person", home_branch_id=main.id)
        make_member(session, church, "East", "Person", home_branch_id=east.id)
        make_membership(session, church, make_user(session, "wide@x.test"), "secretary")
        make_membership(session, church, make_user(session, "east@x.test"), "secretary", branch_id=east.id)
        wide = bearer(login(client, "wide@x.test").json()["data"]["access_token"])
        east_h = bearer(login(client, "east@x.test").json()["data"]["access_token"])
        assert client.get("/api/v1/members/", headers=wide).json()["total"] == 2
        east_list = client.get("/api/v1/members/", headers=east_h).json()
        assert east_list["total"] == 1 and east_list["data"][0]["first_name"] == "East"
        created = client.post("/api/v1/visitors/", json={"first_name": "Guest", "phone": "0201112222"}, headers=east_h)
        assert created.json()["data"]["branch_id"] == str(east.id)
        assert client.get("/api/v1/visitors/", headers=wide).json()["total"] == 1

    def test_user_in_two_churches_sees_only_active(self, client, session):
        a = make_church(session, "first-ch")
        b = make_church(session, "second-ch")
        for c in (a, b):
            make_branch(session, c, "Main", is_main=True)
        make_member(session, a, "Only", "InA")
        make_member(session, b, "Only", "InB")
        user = make_user(session, "both@x.test")
        make_membership(session, a, user, "church_admin")
        make_membership(session, b, user, "church_admin")
        data = login(client, "both@x.test").json()["data"]
        assert data["active_church"] is None and len(data["churches"]) == 2
        assert client.get("/api/v1/members/", headers=bearer(data["access_token"])).status_code == 403
        switched = client.post("/api/v1/auth/switch-church", json={"church_id": str(b.id)},
                               headers=bearer(data["access_token"])).json()["data"]
        names = [m["last_name"] for m in client.get("/api/v1/members/", headers=bearer(switched["access_token"])).json()["data"]]
        assert names == ["InB"]


def test_login_rate_limited(client, session):
    make_user(session, "rl@x.test")
    codes = [client.post("/api/v1/auth/login", json={"email": "rl@x.test", "password": "bad"}).status_code
             for _ in range(12)]
    assert codes[:10] == [401] * 10 and codes[-1] == 429


def test_manual_provider_invoice_confirmed_by_operator(client, session, monkeypatch):
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "manual")
    owner = bearer(signup(client).json()["data"]["access_token"])
    r = client.post("/api/v1/billing/checkout", json={"plan_code": "growth"}, headers=owner).json()["data"]
    invoice = r["invoice"]
    assert invoice["provider"] == "manual" and invoice["number"] in invoice["payment_instructions"]
    # The church cannot complete it itself.
    assert client.post(f"/api/v1/billing/fake/complete/{invoice['id']}", headers=owner).status_code == 404
    make_user(session, "ops2@platform.test", is_platform_admin=True)
    ops = bearer(login(client, "ops2@platform.test").json()["data"]["access_token"])
    paid = client.post(f"/api/v1/platform/invoices/{invoice['id']}/mark-paid", headers=ops)
    assert paid.status_code == 200 and paid.json()["data"]["status"] == "paid"
    sub = client.get("/api/v1/billing/subscription", headers=owner).json()["data"]
    assert sub["church_status"] == "active" and sub["status"] == "active"
    assert client.post(f"/api/v1/platform/invoices/{invoice['id']}/mark-paid", headers=ops).status_code == 400
