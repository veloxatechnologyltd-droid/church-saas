"""Outreach features through the real API: visitors, prayer requests, pledges, self check-in,
public forms, and cross-church isolation for all of them."""
import uuid
from datetime import date

import pytest

from app.models import AttendanceRecord, AuditLog, Donation, Member, PrayerRequest, Visitor
from tests.helpers import (
    make_branch, make_church, make_fund, make_member, make_membership, make_session, make_user,
)
from tests.test_auth_api import bearer, login

V = "/api/v1/visitors/"
P = "/api/v1/prayer-requests/"
C = "/api/v1/pledges/campaigns"
PUB = "/api/v1/public"


@pytest.fixture()
def church(session):
    church = make_church(session, "grace-chapel")
    make_branch(session, church, "Main", is_main=True)
    return church


@pytest.fixture()
def other_church(session):
    church = make_church(session, "other-church")
    make_branch(session, church, "Main", is_main=True)
    return church


def _token(client, session, church, email, role="church_admin"):
    make_membership(session, church, make_user(session, email), role)
    return login(client, email).json()["data"]["access_token"]


@pytest.fixture()
def admin(client, session, church):
    return bearer(_token(client, session, church, "admin@grace.test"))


@pytest.fixture()
def other_admin(client, session, other_church):
    return bearer(_token(client, session, other_church, "admin@other.test"))


# ------------------------------------------------------------------ visitors

class TestVisitors:
    def test_crud_and_summary(self, client, session, church, admin):
        created = client.post(V, json={"first_name": "Kofi", "last_name": "Asante", "phone": "024 111 2222",
                                       "how_heard": "Friend"}, headers=admin)
        assert created.status_code == 201, created.text
        vid = created.json()["data"]["id"]
        data = created.json()["data"]
        assert data["status"] == "new" and data["source"] == "manual" and data["visit_date"] == date.today().isoformat()
        assert data["branch_id"] is not None  # stamped with the main branch

        listed = client.get(V, params={"search": "kofi"}, headers=admin).json()
        assert listed["total"] == 1 and listed["data"][0]["id"] == vid

        updated = client.put(f"{V}{vid}", json={"notes": "Lives in Tema"}, headers=admin)
        assert updated.status_code == 200 and updated.json()["data"]["notes"] == "Lives in Tema"

        contacted = client.post(f"{V}{vid}/contacted", json={"notes": "Called"}, headers=admin).json()["data"]
        assert contacted["status"] == "contacted" and contacted["last_contacted_at"] and "Called" in contacted["notes"]

        summary = client.get(f"{V}summary", headers=admin).json()["data"]
        assert summary["contacted"] == 1 and summary["total"] == 1 and summary["by_source"]["manual"] == 1

        assert client.delete(f"{V}{vid}", headers=admin).status_code == 204
        assert client.get(f"{V}{vid}", headers=admin).status_code == 404
        assert session.query(AuditLog).filter_by(table_name="visitors", action="deleted").count() == 1

    def test_convert_creates_a_member(self, client, session, church, admin):
        vid = client.post(V, json={"first_name": "Esi", "last_name": "Boateng", "phone": "0201234567",
                                   "email": "esi@x.test"}, headers=admin).json()["data"]["id"]
        response = client.post(f"{V}{vid}/convert", headers=admin)
        assert response.status_code == 200, response.text
        body = response.json()["data"]
        assert body["visitor"]["status"] == "converted"
        assert body["visitor"]["converted_member_id"] == body["member"]["id"]
        member = session.get(Member, uuid.UUID(body["member"]["id"]))
        assert member.church_id == church.id and member.phone == "0201234567" and member.date_joined == date.today()
        assert client.post(f"{V}{vid}/convert", headers=admin).status_code == 409

    def test_member_role_cannot_see_visitors(self, client, session, church):
        headers = bearer(_token(client, session, church, "m@grace.test", "member"))
        assert client.get(V, headers=headers).status_code == 403

    def test_group_leader_reads_but_cannot_write(self, client, session, church):
        headers = bearer(_token(client, session, church, "gl@grace.test", "group_leader"))
        assert client.get(V, headers=headers).status_code == 200
        assert client.post(V, json={"first_name": "X"}, headers=headers).status_code == 403


# ------------------------------------------------------------------ prayer

class TestPrayer:
    def test_crud(self, client, session, church, admin):
        member = make_member(session, church, "Akua", "Owusu")
        created = client.post(P, json={"member_id": str(member.id), "request": "Healing for my mother",
                                       "category": "healing"}, headers=admin)
        assert created.status_code == 201, created.text
        rid = created.json()["data"]["id"]
        assert created.json()["data"]["name"] == "Akua Owusu"

        prayed = client.post(f"{P}{rid}/prayed", headers=admin).json()["data"]
        assert prayed["prayed_count"] == 1 and prayed["status"] == "praying"

        answered = client.put(f"{P}{rid}", json={"status": "answered", "response_notes": "Discharged"}, headers=admin)
        assert answered.json()["data"]["status"] == "answered"
        assert client.get(P, params={"status": "answered"}, headers=admin).json()["total"] == 1
        assert client.delete(f"{P}{rid}", headers=admin).status_code == 204

    def test_unknown_member_is_rejected(self, client, session, church, other_church, admin):
        foreign = make_member(session, other_church, "Other", "Person")
        response = client.post(P, json={"member_id": str(foreign.id), "request": "Something"}, headers=admin)
        assert response.status_code == 400


# ------------------------------------------------------------------ pledges

class TestPledges:
    def test_campaign_pledge_payment_and_progress(self, client, session, church, admin):
        fund = make_fund(session, church, "Building Fund", "building")
        member = make_member(session, church, "Yaw", "Mensah", phone="0244000000")
        camp = client.post(C, json={"name": "New Sanctuary", "fund_id": str(fund.id), "target_amount": 10000,
                                    "start_date": "2026-01-01"}, headers=admin)
        assert camp.status_code == 201, camp.text
        cid = camp.json()["data"]["id"]

        p1 = client.post(f"{C}/{cid}/pledges", json={"member_id": str(member.id), "amount": 1000}, headers=admin)
        assert p1.status_code == 201, p1.text
        pid = p1.json()["data"]["id"]
        p2 = client.post(f"{C}/{cid}/pledges", json={"pledger_name": "Visiting Elder", "amount": 500}, headers=admin)
        assert p2.status_code == 201
        assert client.post(f"{C}/{cid}/pledges", json={"amount": 5}, headers=admin).status_code == 422

        paid = client.post(f"/api/v1/pledges/{pid}/payments",
                           json={"amount": 400, "paid_on": "2026-02-01", "payment_method": "momo"}, headers=admin)
        assert paid.status_code == 201, paid.text
        pledge = paid.json()["data"]
        assert pledge["paid"] == 400 and pledge["balance"] == 600 and pledge["status"] in ("partial", "overdue")
        donation = session.query(Donation).filter(Donation.fund_id == fund.id).one()
        assert float(donation.amount) == 400 and donation.member_id == member.id and donation.church_id == church.id
        assert pledge["payments"][0]["donation_id"] == str(donation.id)

        client.post(f"/api/v1/pledges/{pid}/payments", json={"amount": 600, "paid_on": "2026-03-01"}, headers=admin)
        detail = client.get(f"{C}/{cid}", headers=admin).json()["data"]
        assert detail["pledged_total"] == 1500 and detail["paid_total"] == 1000 and detail["pledge_count"] == 2
        assert detail["progress_pct"] == 10.0  # of the 10,000 target
        statuses = {p["display_name"]: p["status"] for p in detail["pledges"]}
        assert statuses["Yaw Mensah"] == "fulfilled" and statuses["Visiting Elder"] == "unpaid"

        listed = client.get(C, headers=admin).json()["data"]
        assert listed[0]["paid_total"] == 1000

        assert client.delete(f"/api/v1/pledges/{pid}", headers=admin).status_code == 204
        assert client.get(f"{C}/{cid}", headers=admin).json()["data"]["pledge_count"] == 1

    def test_campaign_without_fund_records_no_donation(self, client, session, church, admin):
        cid = client.post(C, json={"name": "Harvest", "start_date": "2026-01-01"}, headers=admin).json()["data"]["id"]
        pid = client.post(f"{C}/{cid}/pledges", json={"pledger_name": "Anon", "amount": 50},
                          headers=admin).json()["data"]["id"]
        client.post(f"/api/v1/pledges/{pid}/payments", json={"amount": 50, "paid_on": "2026-01-02"}, headers=admin)
        assert session.query(Donation).count() == 0

    def test_secretary_cannot_manage_pledges(self, client, session, church):
        headers = bearer(_token(client, session, church, "sec@grace.test", "secretary"))
        assert client.get(C, headers=headers).status_code == 403


# ------------------------------------------------------------------ public forms

class TestPublicForms:
    def test_branding(self, client, church):
        data = client.get(f"{PUB}/churches/grace-chapel").json()["data"]
        assert data["name"] == "Grace Chapel" and "id" not in data
        assert client.get(f"{PUB}/churches/nope").status_code == 404

    def test_suspended_church_is_hidden(self, client, session, church):
        church.status = "suspended"
        session.flush()
        assert client.get(f"{PUB}/churches/grace-chapel").status_code == 404
        assert client.post(f"{PUB}/churches/grace-chapel/visitors",
                           json={"first_name": "A", "phone": "0241112222"}).status_code == 404

    def test_welcome_card_creates_then_dedupes(self, client, session, church):
        url = f"{PUB}/churches/grace-chapel/visitors"
        assert client.post(url, json={"first_name": "Ama", "phone": "024 555 6666"}).status_code == 201
        assert client.post(url, json={"first_name": "Ama", "phone": "+233245556666",
                                      "prayer_request": "Job"}).status_code == 201
        visitor = session.query(Visitor).one()
        assert visitor.church_id == church.id and visitor.source == "form"
        assert visitor.visit_count == 2 and visitor.status == "returning" and visitor.prayer_request == "Job"
        assert visitor.branch_id is not None

    def test_welcome_card_needs_contact_and_honeypot_drops(self, client, session, church):
        url = f"{PUB}/churches/grace-chapel/visitors"
        assert client.post(url, json={"first_name": "NoContact"}).status_code == 422
        bot = client.post(url, json={"first_name": "Bot", "phone": "0240000000", "website": "http://spam"})
        assert bot.status_code == 201
        assert session.query(Visitor).count() == 0

    def test_prayer_form(self, client, session, church):
        url = f"{PUB}/churches/grace-chapel/prayer-requests"
        assert client.post(url, json={"request": "Pray for exams", "is_confidential": True}).status_code == 201
        assert client.post(url, json={"request": "spam", "website": "x"}).status_code == 201
        row = session.query(PrayerRequest).one()
        assert row.church_id == church.id and row.source == "form" and row.is_confidential and row.name is None
        assert client.post(url, json={"request": ""}).status_code == 422


# ------------------------------------------------------------------ self check-in

class TestSelfCheckin:
    def test_flow(self, client, session, church, admin):
        member = make_member(session, church, "Kwame", "Nkrumah", phone="+233 24 123 4567")
        service = make_session(session, church)
        toggled = client.post(f"/api/v1/attendance/sessions/{service.id}/checkin", json={"open": True}, headers=admin)
        assert toggled.status_code == 200, toggled.text
        code = toggled.json()["data"]["checkin_code"]
        assert code and toggled.json()["data"]["checkin_url"].endswith(f"/checkin/{code}")

        info = client.get(f"{PUB}/checkin/{code}").json()["data"]
        assert info["church"]["name"] == "Grace Chapel" and info["session"]["title"] == "Sunday"

        first = client.post(f"{PUB}/checkin/{code}", json={"phone": "0241234567"}).json()["data"]
        assert first == {"status": "checked_in", "first_name": "Kwame"}
        again = client.post(f"{PUB}/checkin/{code}", json={"phone": "233-24-123-4567"}).json()["data"]
        assert again["status"] == "already_checked_in"
        record = session.query(AttendanceRecord).one()
        assert record.member_id == member.id and record.source == "self_checkin" and record.church_id == church.id

        unknown = client.post(f"{PUB}/checkin/{code}", json={"phone": "0209999999"}).json()["data"]
        assert unknown["status"] == "not_found"

        closed = client.post(f"/api/v1/attendance/sessions/{service.id}/checkin", json={"open": False}, headers=admin)
        assert closed.json()["data"]["checkin_code"] == code  # kept for reopening
        assert client.get(f"{PUB}/checkin/{code}").status_code == 404
        assert client.post(f"{PUB}/checkin/{code}", json={"phone": "0241234567"}).status_code == 404

    def test_checkin_never_matches_another_churchs_member(self, client, session, church, other_church, admin):
        make_member(session, other_church, "Other", "Member", phone="0241234567")
        service = make_session(session, church)
        code = client.post(f"/api/v1/attendance/sessions/{service.id}/checkin", json={"open": True},
                           headers=admin).json()["data"]["checkin_code"]
        assert client.post(f"{PUB}/checkin/{code}", json={"phone": "0241234567"}).json()["data"]["status"] == "not_found"

    def test_member_role_cannot_toggle(self, client, session, church):
        service = make_session(session, church)
        headers = bearer(_token(client, session, church, "m@grace.test", "member"))
        assert client.post(f"/api/v1/attendance/sessions/{service.id}/checkin", json={"open": True},
                           headers=headers).status_code == 403


# ------------------------------------------------------------------ isolation

class TestIsolation:
    def test_church_b_cannot_touch_church_a_outreach(self, client, session, church, admin, other_admin):
        vid = client.post(V, json={"first_name": "A"}, headers=admin).json()["data"]["id"]
        rid = client.post(P, json={"request": "A's request"}, headers=admin).json()["data"]["id"]
        cid = client.post(C, json={"name": "A campaign", "start_date": "2026-01-01"}, headers=admin).json()["data"]["id"]
        pid = client.post(f"{C}/{cid}/pledges", json={"pledger_name": "A", "amount": 10},
                          headers=admin).json()["data"]["id"]
        service = make_session(session, church)

        b = other_admin
        for method, url, body in [
            ("get", f"{V}{vid}", None), ("put", f"{V}{vid}", {"notes": "x"}), ("delete", f"{V}{vid}", None),
            ("post", f"{V}{vid}/contacted", {}), ("post", f"{V}{vid}/convert", None),
            ("put", f"{P}{rid}", {"status": "closed"}), ("post", f"{P}{rid}/prayed", None), ("delete", f"{P}{rid}", None),
            ("get", f"{C}/{cid}", None), ("put", f"{C}/{cid}", {"name": "Hijack"}),
            ("post", f"{C}/{cid}/pledges", {"pledger_name": "B", "amount": 1}),
            ("post", f"/api/v1/pledges/{pid}/payments", {"amount": 1, "paid_on": "2026-01-01"}),
            ("delete", f"/api/v1/pledges/{pid}", None),
            ("post", f"/api/v1/attendance/sessions/{service.id}/checkin", {"open": True}),
        ]:
            kwargs = {"headers": b}
            if body is not None:
                kwargs["json"] = body
            response = getattr(client, method)(url, **kwargs)
            assert response.status_code == 404, (method, url, response.status_code, response.text)

        assert client.get(V, headers=b).json()["total"] == 0
        assert client.get(P, headers=b).json()["total"] == 0
        assert client.get(C, headers=b).json()["total"] == 0
        assert client.get(f"{V}summary", headers=b).json()["data"]["total"] == 0

    def test_cannot_link_a_campaign_to_another_churchs_fund(self, client, session, other_church, admin):
        foreign_fund = make_fund(session, other_church, "Their fund", "theirs")
        response = client.post(C, json={"name": "Hijack", "fund_id": str(foreign_fund.id), "start_date": "2026-01-01"},
                               headers=admin)
        assert response.status_code == 400
