"""Tenant isolation across EVERY endpoint that takes an id.

Church B owns one of everything. Church A's admin calls every route (enumerated from the
OpenAPI schema, so new routes are covered automatically) with B's ids and a plausible body.
Each call must answer 403/404 and B's data must be unchanged. List/summary endpoints must
never include any of B's ids. A route that takes an id and is not mapped here fails the test,
forcing whoever adds it to think about isolation.
"""
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.models import (
    Announcement, AttendanceSession, Donation, DonationFund, Event, FinanceBatch, Family, Group, Invitation,
    Invoice, Member, PastoralLog, Pledge, PledgeCampaign, PrayerRequest, ReminderSchedule, Visitor,
)
from tests.helpers import make_branch, make_church, make_member, make_membership, make_user
from tests.test_auth_api import bearer, login

# Routes that are not church-scoped by id: public (slug/code), platform (own suite),
# provider webhooks, and the export whose param is a dataset name.
SKIP_PREFIXES = ("/api/v1/public/", "/api/v1/platform/", "/api/v1/billing/webhooks/", "/api/v1/church/export/")


@pytest.fixture()
def world(session, client):
    a = make_church(session, "church-a")
    make_branch(session, a, "A Main", is_main=True)
    a_member = make_member(session, a, "Ama", "Admin")
    make_membership(session, a, make_user(session, "admin@a.test"), "church_admin", member_id=a_member.id)

    b = make_church(session, "church-b")
    b_branch = make_branch(session, b, "B Main", is_main=True)
    b_other_branch = make_branch(session, b, "B East")
    family = Family(church_id=b.id, family_name="Bfam")
    session.add(family)
    session.flush()
    member = make_member(session, b, "Bob", "Bee", family_id=family.id)
    b_user = make_user(session, "admin@b.test")
    b_membership = make_membership(session, b, b_user, "secretary", member_id=member.id)
    fund = DonationFund(church_id=b.id, name="Tithe", code="tithe")
    batch = FinanceBatch(church_id=b.id, title="Sunday", service_date=date(2026, 1, 4))
    session.add_all([fund, batch])
    session.flush()
    donation = Donation(church_id=b.id, fund_id=fund.id, batch_id=batch.id, member_id=member.id, amount=50,
                        donation_date=date(2026, 1, 4))
    att = AttendanceSession(church_id=b.id, title="Service", session_date=date(2026, 1, 4), checkin_code="bcode123",
                            checkin_open=True)
    group = Group(church_id=b.id, name="B Choir")
    event = Event(church_id=b.id, title="B Event", start_datetime=datetime.now(timezone.utc) + timedelta(days=3))
    log = PastoralLog(church_id=b.id, member_id=member.id, log_type="visit", notes="secret", log_date=date(2026, 1, 4))
    ann = Announcement(church_id=b.id, title="B news", body="B only")
    sched = ReminderSchedule(church_id=b.id, name="B reminder", message_template="hi", weekday=6,
                             send_time=datetime(2026, 1, 1, 8).time())
    invitation = Invitation(church_id=b.id, email="new@b.test", role="member", token_hash="x" * 64,
                            expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    visitor = Visitor(church_id=b.id, first_name="Vera", visit_date=date(2026, 1, 4))
    prayer = PrayerRequest(church_id=b.id, request="B prayer")
    campaign = PledgeCampaign(church_id=b.id, name="B Building", start_date=date(2026, 1, 1), fund_id=fund.id)
    invoice = Invoice(church_id=b.id, number="INV-B-1", kind="sms_credits", description="B credits", amount=10,
                      sms_credits=100, status="open", provider="fake")
    session.add_all([donation, att, group, event, log, ann, sched, invitation, visitor, prayer, campaign, invoice])
    session.flush()
    pledge = Pledge(church_id=b.id, campaign_id=campaign.id, member_id=member.id, amount=100)
    session.add(pledge)
    session.flush()

    ids = {
        "member_id": member.id, "family_id": family.id, "session_id": att.id, "donation_id": donation.id,
        "batch_id": batch.id, "group_id": group.id, "event_id": event.id, "log_id": log.id,
        "announcement_id": ann.id, "schedule_id": sched.id, "invitation_id": invitation.id,
        "visitor_id": visitor.id, "request_id": prayer.id, "campaign_id": campaign.id, "pledge_id": pledge.id,
        "branch_id": b_other_branch.id, "membership_id": b_membership.id, "invoice_id": invoice.id,
    }
    token = login(client, "admin@a.test").json()["data"]["access_token"]
    return {"a": a, "b": b, "a_member": a_member, "ids": ids, "headers": bearer(token),
            "b_main_branch": b_branch}


def _body(path: str, method: str, a_member_id) -> dict:
    """A body that would succeed against the caller's own church, so only isolation stops it."""
    m = str(a_member_id)
    if method == "put":
        return {"first_name": "Hacked", "name": "Hacked", "title": "Hacked", "notes": "Hacked", "role": "member",
                "response_notes": "Hacked", "message_template": "Hacked", "body": "Hacked"}
    if path.endswith("/mark"):
        return {"records": [{"member_id": m, "status": "present"}]}
    if path.endswith("/members") or path.endswith("/register"):
        return {"member_id": m}
    if path.endswith("/pledges"):
        return {"pledger_name": "X", "amount": 10}
    if path.endswith("/payments"):
        return {"amount": 5, "paid_on": "2026-01-05"}
    if path.endswith("/checkin"):
        return {"open": True}
    if path.endswith("/contacted"):
        return {"notes": "x"}
    return {}


def _snapshot(session, church_id) -> dict:
    tables = ["members", "families", "attendance_sessions", "attendance_records", "donations", "finance_batches",
              "groups", "group_members", "events", "event_registrations", "pastoral_logs", "announcements",
              "reminder_schedules", "invitations", "visitors", "prayer_requests", "pledge_campaigns", "pledges",
              "pledge_payments", "branches", "memberships", "invoices", "payments"]
    out = {}
    for table in tables:
        rows = session.execute(
            text(f"SELECT md5(string_agg(t::text, ',' ORDER BY t::text)) FROM {table} t WHERE church_id = :c"),
            {"c": church_id},
        ).scalar()
        out[table] = rows
    return out


def test_every_id_route_rejects_another_churchs_ids(client, session, world):
    from app.main import app

    ids = world["ids"]
    headers = world["headers"]
    before = _snapshot(session, world["b"].id)
    checked = 0
    failures = []
    for path, ops in app.openapi()["paths"].items():
        params = re.findall(r"{(\w+)}", path)
        if not params or path.startswith(SKIP_PREFIXES):
            continue
        missing = [p for p in params if p not in ids]
        assert not missing, f"{path}: add a church-B fixture for {missing} so isolation is tested"
        url = path
        for p in params:
            url = url.replace("{" + p + "}", str(ids[p]))
        for method in ops:
            if path.endswith("/photo"):
                response = client.post(url, headers=headers, files={"file": ("x.png", b"\x89PNG", "image/png")})
            elif method in ("get", "delete"):
                response = client.request(method.upper(), url, headers=headers)
            else:
                response = client.request(method.upper(), url, headers=headers,
                                          json=_body(path, method, world["a_member"].id))
            checked += 1
            if response.status_code not in (403, 404):
                failures.append(f"{method.upper()} {path} -> {response.status_code} {response.text[:150]}")
    assert not failures, "Cross-church access not rejected:\n" + "\n".join(failures)
    assert checked >= 50
    session.expire_all()
    assert _snapshot(session, world["b"].id) == before, "church B's data changed"


def test_list_endpoints_never_leak_another_churchs_ids(client, session, world):
    from app.main import app

    secrets = {str(v) for v in world["ids"].values()} | {str(world["b"].id), str(world["b_main_branch"].id)}
    leaks = []
    for path, ops in app.openapi()["paths"].items():
        if "get" not in ops or "{" in path or path.startswith(("/api/v1/platform", "/api/v1/public")):
            continue
        if not path.startswith("/api/v1/"):
            continue
        response = client.get(path, headers=world["headers"])
        body = response.text
        for secret in secrets:
            if secret in body:
                leaks.append(f"GET {path} leaks {secret}")
    assert not leaks, "\n".join(leaks)


def test_rls_blocks_raw_sql_for_another_church(session, world):
    """The database backstop: with app.current_church set, a non-superuser role sees only
    that church's rows even through raw SQL."""
    session.execute(text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rls_probe') THEN
                CREATE ROLE rls_probe NOLOGIN;
            END IF;
        END $$;
    """))
    session.execute(text("GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO rls_probe"))
    session.execute(text("SELECT set_config('app.current_church', :c, true)"), {"c": str(world["a"].id)})
    session.execute(text("SET LOCAL ROLE rls_probe"))
    try:
        churches = session.execute(text("SELECT DISTINCT church_id FROM members")).scalars().all()
        assert churches == [world["a"].id]
        assert session.execute(text("SELECT count(*) FROM visitors")).scalar() == 0
        from sqlalchemy.exc import ProgrammingError

        with pytest.raises(ProgrammingError):  # WITH CHECK refuses writing into church B
            with session.begin_nested():
                session.execute(
                    text("INSERT INTO families (id, church_id, family_name) VALUES (gen_random_uuid(), :b, 'x')"),
                    {"b": world["b"].id},
                )
    finally:
        session.execute(text("RESET ROLE"))
