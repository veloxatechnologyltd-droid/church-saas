"""Seed realistic, fully synthetic demo data (local development and demo environments).

    cd backend && python scripts/seed_demo.py            # add demo churches (skips existing ones)
    cd backend && python scripts/seed_demo.py --reset    # wipe ALL data first (local DB only)

Creates a platform operator and three churches:

* Grace Covenant Church (grace-covenant)   - Growth plan, paid, 2 branches, ~180 members,
  16 weeks of attendance, giving, expenses, groups, events, visitors, prayer requests,
  a building pledge campaign, pastoral follow-ups, SMS history.
* Living Waters Assembly (living-waters)   - on trial, Kumasi, smaller.
* Bethel Fellowship (bethel-fellowship)    - suspended (to demo the platform console).

Every person, phone number and email here is invented. Logins (password ``Demo@12345``):

    owner@asafo.demo        platform admin
    pastor@grace.demo          church_admin, Grace Covenant (also member of Living Waters)
    secretary@grace.demo       secretary
    finance@grace.demo         finance
    youth@grace.demo           group_leader (Youth Ministry)
    tema@grace.demo            church_admin limited to the Tema branch
    admin@livingwaters.demo    church_admin, Living Waters
"""
from __future__ import annotations

import argparse
import os
import random
import secrets
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(Path(__file__).resolve().parents[1])

from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.db.tenancy import bind_tenant, clear_tenant  # noqa: E402
from app.models import (  # noqa: E402
    Announcement, AttendanceRecord, AttendanceSession, AuditLog, Branch, Church, Communication, Donation,
    DonationFund, Event, EventRegistration, Expense, ExpenseCategory, Family, FinanceBatch, Group, GroupMember,
    Invoice, Member, Membership, Payment, PastoralLog, Pledge, PledgeCampaign, PledgePayment, PrayerRequest,
    ReminderSchedule, Subscription, User, Visitor,
)
from app.services import sms_credits  # noqa: E402
from app.services.onboarding import create_church  # noqa: E402

PASSWORD = "Demo@12345"
rng = random.Random(20261109)
TODAY = date.today()
NOW = datetime.now(timezone.utc)

MALE = ["Kwame", "Kofi", "Kwabena", "Kwaku", "Yaw", "Kojo", "Kwesi", "Emmanuel", "Daniel", "Samuel", "Joseph",
        "Isaac", "Michael", "Prince", "Richard", "Ebenezer", "Nana", "Eric", "Felix", "Godwin", "Benjamin", "Elijah"]
FEMALE = ["Akosua", "Ama", "Abena", "Akua", "Yaa", "Afia", "Adwoa", "Esi", "Efua", "Grace", "Mercy", "Patience",
          "Comfort", "Gifty", "Joyce", "Priscilla", "Esther", "Deborah", "Vida", "Linda", "Naa", "Dzifa", "Selasie"]
LAST = ["Mensah", "Owusu", "Boateng", "Asante", "Osei", "Agyeman", "Appiah", "Amoah", "Ofori", "Darko", "Addo",
        "Quaye", "Tetteh", "Annan", "Ansah", "Frimpong", "Badu", "Nkrumah", "Sarpong", "Opoku", "Acheampong",
        "Kumi", "Adjei", "Bonsu", "Amponsah", "Gyamfi", "Antwi", "Danso", "Kyei", "Lamptey", "Okyere", "Afriyie"]
OCCUPATIONS = ["Teacher", "Nurse", "Trader", "Engineer", "Accountant", "Student", "Driver", "Banker", "Farmer",
               "Seamstress", "Civil servant", "Entrepreneur", "Pharmacist", "IT specialist", "Retired", "Caterer"]
AREAS_ACCRA = ["East Legon", "Madina", "Adenta", "Spintex", "Osu", "Dansoman", "Achimota", "Kasoa", "Teshie",
               "Lapaz", "Dome", "Haatso"]
AREAS_TEMA = ["Community 25", "Community 11", "Sakumono", "Ashaiman", "Lashibi", "Community 4"]
AREAS_KSI = ["Bantama", "Asokwa", "Adum", "Ahodwo", "Suame", "Tafo"]
HOW_HEARD = ["Friend or family", "Walked past", "Social media", "Radio", "Crusade", "Invited by a member"]
PRAYERS = [
    ("healing", "Please pray for my mother who is recovering from surgery at Korle Bu."),
    ("finances", "Pray for a breakthrough in my business this quarter."),
    ("family", "Pray for peace and unity in my home."),
    ("salvation", "Pray for my brother to give his life to Christ."),
    ("thanksgiving", "Thank God with me — I passed my nursing licensing exam!"),
    ("other", "Pray for journey mercies as I travel to Takoradi for work."),
    ("healing", "Pray for my child's recovery from malaria."),
    ("finances", "Pray that I find a job after national service."),
    ("family", "Pray for my marriage, we are going through a difficult season."),
    ("thanksgiving", "God blessed us with a baby boy. Thank you church family!"),
]


def phone() -> str:
    prefix = rng.choice(["024", "054", "055", "020", "050", "027", "026", "059"])
    return f"{prefix}{rng.randint(1000000, 9999999)}"


def user(db, email: str, platform_admin: bool = False) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing
    u = User(email=email, hashed_password=hash_password(PASSWORD), is_active=True, is_platform_admin=platform_admin)
    db.add(u)
    db.flush()
    return u


def add_login(db, church: Church, email: str, role: str, member: Member | None, branch_id=None) -> None:
    u = user(db, email)
    db.add(Membership(church_id=church.id, user_id=u.id, role=role, member_id=member.id if member else None,
                      branch_id=branch_id))
    db.flush()


def make_members(db, n: int, branches: list[tuple[Branch, list[str]]]) -> list[Member]:
    members: list[Member] = []
    families: list[Family] = []
    for _ in range(n // 4):
        fam = Family(family_name=rng.choice(LAST))
        db.add(fam)
        families.append(fam)
    db.flush()
    for i in range(n):
        female = rng.random() < 0.56
        first = rng.choice(FEMALE if female else MALE)
        family = rng.choice(families) if families and rng.random() < 0.55 else None
        last = family.family_name if family else rng.choice(LAST)
        branch, areas = rng.choices(branches, weights=[3] + [1] * (len(branches) - 1))[0]
        age = rng.choice([rng.randint(8, 17), rng.randint(18, 35), rng.randint(18, 35), rng.randint(36, 60),
                          rng.randint(36, 60), rng.randint(61, 82)])
        dob = TODAY - timedelta(days=age * 365 + rng.randint(0, 364))
        # Put a handful of birthdays this week so the dashboard has something to show.
        if i % 37 == 0:
            dob = dob.replace(month=TODAY.month, day=min(28, TODAY.day + rng.randint(0, 5)))
        joined = TODAY - timedelta(days=rng.randint(10, 9 * 365))
        status = "active" if rng.random() < 0.9 else rng.choice(["inactive", "visitor"])
        m = Member(
            first_name=first, last_name=last, gender="female" if female else "male", date_of_birth=dob,
            phone=phone() if age >= 16 else None,
            email=f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@example.com" if age >= 18 and rng.random() < 0.6 else None,
            address=f"{rng.choice(areas)}, {'Tema' if branch.name == 'Tema' else ('Kumasi' if areas is AREAS_KSI else 'Accra')}",
            occupation=rng.choice(OCCUPATIONS) if age >= 18 else "Student",
            marital_status=rng.choice(["single", "married", "married", "widowed"]) if age >= 22 else "single",
            membership_status=status, date_joined=joined,
            baptism_date=joined + timedelta(days=rng.randint(30, 400)) if rng.random() < 0.6 else None,
            membership_class_completed=rng.random() < 0.7, family_id=family.id if family else None,
            is_family_head=bool(family) and rng.random() < 0.25, home_branch_id=branch.id,
            introduced_by=rng.choice(LAST) + " family" if rng.random() < 0.2 else None,
        )
        db.add(m)
        members.append(m)
    db.flush()
    return members


def sundays(weeks: int) -> list[date]:
    last_sunday = TODAY - timedelta(days=(TODAY.weekday() + 1) % 7)
    return [last_sunday - timedelta(weeks=w) for w in range(weeks)][::-1]


def seed_attendance(db, church_user: User, members: list[Member], branches: list[Branch], weeks: int) -> None:
    # Each member gets a personal attendance tendency; a few drift away recently (care alerts).
    tendency = {m.id: rng.choice([0.92, 0.85, 0.75, 0.6, 0.4]) for m in members}
    drifting = set(rng.sample([m.id for m in members if m.membership_status == "active"], k=max(3, len(members) // 20)))
    for idx, day in enumerate(sundays(weeks)):
        for branch in branches:
            session = AttendanceSession(
                title="Sunday Service" if branch.is_main else f"Sunday Service - {branch.name}", session_date=day,
                session_type="sunday_service", session_start_time=time(8, 30), branch_id=branch.id,
                created_by=church_user.id, first_timer_count=rng.randint(1, 6),
            )
            db.add(session)
            db.flush()
            for m in members:
                if m.home_branch_id != branch.id or m.membership_status == "inactive":
                    continue
                p = tendency[m.id]
                if m.id in drifting and idx >= weeks - 4:
                    p = 0.0
                status = "present" if rng.random() < p else rng.choice(["absent", "absent", "excused"])
                db.add(AttendanceRecord(
                    session_id=session.id, member_id=m.id, status=status,
                    checked_in_at=datetime.combine(day, time(8, rng.randint(15, 59)), tzinfo=timezone.utc) if status == "present" else None,
                    source="self_checkin" if status == "present" and rng.random() < 0.3 else "manual",
                ))
        # Midweek service on the main branch.
        midweek = day + timedelta(days=3)
        if midweek <= TODAY:
            s = AttendanceSession(title="Wednesday Bible Study", session_date=midweek, session_type="midweek",
                                  session_start_time=time(18, 30), branch_id=branches[0].id, created_by=church_user.id)
            db.add(s)
            db.flush()
            for m in members:
                if m.home_branch_id == branches[0].id and m.membership_status == "active" and rng.random() < tendency[m.id] * 0.45:
                    db.add(AttendanceRecord(session_id=s.id, member_id=m.id, status="present"))
    db.flush()


def seed_finance(db, church_user: User, members: list[Member], branches: list[Branch], weeks: int, scale: float) -> dict:
    funds = {f.code: f for f in db.query(DonationFund).all()}
    cats = {c.name: c for c in db.query(ExpenseCategory).all()}
    tithers = [m for m in members if m.membership_status == "active" and m.occupation not in ("Student",)]
    for day in sundays(weeks):
        for branch in branches:
            batch = FinanceBatch(title=f"Sunday {day.strftime('%d %b')}" + ("" if branch.is_main else f" - {branch.name}"),
                                 service_date=day, service_type="sunday_service", branch_id=branch.id,
                                 recorded_by=church_user.id, is_closed=day < TODAY - timedelta(days=6))
            db.add(batch)
            db.flush()
            db.add(Donation(fund_id=funds["offering"].id, batch_id=batch.id, branch_id=branch.id,
                            amount=Decimal(round(rng.uniform(900, 2600) * scale * (1 if branch.is_main else 0.4), 2)),
                            donation_date=day, payment_method="cash", recorded_by=church_user.id))
            for m in tithers:
                if m.home_branch_id == branch.id and rng.random() < 0.28:
                    db.add(Donation(fund_id=funds["tithe"].id, batch_id=batch.id, member_id=m.id, branch_id=branch.id,
                                    amount=Decimal(rng.choice([50, 80, 100, 120, 150, 200, 250, 300, 500, 800])),
                                    donation_date=day, payment_method=rng.choice(["cash", "momo", "momo", "bank"]),
                                    recorded_by=church_user.id))
            if rng.random() < 0.3:
                db.add(Donation(fund_id=funds["thanksgiving"].id, batch_id=batch.id, branch_id=branch.id,
                                member_id=rng.choice(tithers).id, amount=Decimal(rng.choice([200, 300, 500, 1000])),
                                donation_date=day, payment_method="momo", notes="Thanksgiving offering",
                                recorded_by=church_user.id))
    # Monthly expenses for the last 4 months.
    for months_back in range(4):
        d = (TODAY.replace(day=1) - timedelta(days=30 * months_back)).replace(day=5)
        for name, lo, hi, vendor in [("Utilities", 900, 1600, "ECG / Ghana Water"), ("Payroll", 6000, 6500, "Staff stipends"),
                                     ("Maintenance", 300, 1800, "Kwesi Repairs Ltd"), ("Programs", 500, 2500, "Event logistics"),
                                     ("Welfare", 400, 1500, "Member welfare"), ("Missions", 300, 1200, "Outreach team")]:
            if name in cats:
                db.add(Expense(category_id=cats[name].id, branch_id=branches[0].id,
                               amount=Decimal(round(rng.uniform(lo, hi) * scale, 2)), expense_date=d,
                               payment_method=rng.choice(["bank", "momo", "cash"]), vendor_name=vendor,
                               recorded_by=church_user.id))
    db.flush()
    return funds


def seed_groups(db, members: list[Member]) -> dict[str, Group]:
    specs = [("Choir", "Praise and worship team"), ("Ushering", "Welcome and order during services"),
             ("Youth Ministry", "Ages 18-35"), ("Men's Fellowship", "Brotherhood and accountability"),
             ("Women's Fellowship", "Sisters in Christ"), ("Children's Ministry", "Sunday school teachers"),
             ("Media & Tech", "Sound, projection and livestream"), ("Evangelism", "Outreach and follow-up")]
    adults = [m for m in members if m.date_of_birth and (TODAY - m.date_of_birth).days > 18 * 365]
    groups = {}
    for name, desc in specs:
        pool = adults
        if name == "Men's Fellowship":
            pool = [m for m in adults if m.gender == "male"]
        elif name == "Women's Fellowship":
            pool = [m for m in adults if m.gender == "female"]
        elif name == "Youth Ministry":
            pool = [m for m in adults if (TODAY - m.date_of_birth).days < 36 * 365]
        chosen = rng.sample(pool, k=min(len(pool), rng.randint(8, 26)))
        g = Group(name=name, description=desc, leader_id=chosen[0].id if chosen else None)
        db.add(g)
        db.flush()
        for m in chosen:
            db.add(GroupMember(group_id=g.id, member_id=m.id))
        groups[name] = g
    db.flush()
    return groups


def seed_outreach(db, church: Church, staff: User, members: list[Member], funds: dict, areas: list[str],
                  campaign: bool) -> None:
    # Visitors over the last 10 weeks, in every pipeline stage.
    for i in range(34 if campaign else 9):
        first = rng.choice(FEMALE + MALE)
        visit = TODAY - timedelta(days=rng.randint(0, 70))
        status = rng.choices(["new", "contacted", "returning", "converted", "not_interested"], [5, 4, 3, 2, 1])[0]
        v = Visitor(first_name=first, last_name=rng.choice(LAST), phone=phone(), visit_date=visit,
                    how_heard=rng.choice(HOW_HEARD), address=rng.choice(areas),
                    age_group=rng.choice(["youth", "adult", "adult", "senior"]),
                    invited_by=f"{rng.choice(FEMALE + MALE)} {rng.choice(LAST)}" if rng.random() < 0.4 else None,
                    wants_visit=rng.random() < 0.3, interested_in_membership=rng.random() < 0.5,
                    prayer_request=rng.choice(PRAYERS)[1] if rng.random() < 0.25 else None, status=status,
                    visit_count=1 if status in ("new", "contacted") else rng.randint(2, 5),
                    source=rng.choice(["form", "form", "manual"]),
                    last_contacted_at=NOW - timedelta(days=rng.randint(0, 20)) if status != "new" else None,
                    assigned_to=staff.id if status in ("contacted", "returning") else None)
        if status == "converted":
            m = Member(first_name=v.first_name, last_name=v.last_name, phone=v.phone, membership_status="active",
                       date_joined=visit + timedelta(days=21))
            db.add(m)
            db.flush()
            v.converted_member_id = m.id
        db.add(v)
    for i, (cat, req) in enumerate(PRAYERS if campaign else PRAYERS[:4]):
        m = rng.choice(members) if rng.random() < 0.6 else None
        db.add(PrayerRequest(member_id=m.id if m else None, name=f"{m.first_name} {m.last_name}" if m else rng.choice([None, "Ama K."]),
                             request=req, category=cat, is_confidential=rng.random() < 0.2,
                             status=rng.choice(["new", "new", "praying", "praying", "answered"]),
                             prayed_count=rng.randint(0, 14), source=rng.choice(["form", "manual"])))
    if campaign:
        camp = PledgeCampaign(name="Sanctuary Building Project", description="New 1,200-seat sanctuary at East Legon.",
                              fund_id=funds["building_fund"].id, target_amount=Decimal(250000),
                              start_date=TODAY - timedelta(days=120), end_date=TODAY + timedelta(days=245),
                              created_by=staff.id)
        harvest = PledgeCampaign(name="Harvest 2026", description="Annual harvest and thanksgiving.",
                                 fund_id=funds["harvest"].id, target_amount=Decimal(60000),
                                 start_date=TODAY - timedelta(days=40), end_date=TODAY + timedelta(days=20),
                                 created_by=staff.id)
        db.add_all([camp, harvest])
        db.flush()
        for c, n, amounts in ((camp, 42, [1000, 2000, 2500, 5000, 10000]), (harvest, 28, [200, 300, 500, 1000])):
            for m in rng.sample([m for m in members if m.membership_status == "active"], k=n):
                pledge = Pledge(campaign_id=c.id, member_id=m.id, amount=Decimal(rng.choice(amounts)),
                                due_date=c.end_date)
                db.add(pledge)
                db.flush()
                paid_ratio = rng.choice([0, 0.25, 0.5, 0.5, 0.75, 1, 1])
                remaining = pledge.amount * Decimal(str(paid_ratio))
                installments = rng.randint(1, 3)
                for k in range(installments):
                    if remaining <= 0:
                        break
                    amt = (remaining / (installments - k)).quantize(Decimal("1"))
                    paid_on = c.start_date + timedelta(days=rng.randint(1, max(1, (TODAY - c.start_date).days)))
                    donation = Donation(fund_id=c.fund_id, member_id=m.id, amount=amt, donation_date=paid_on,
                                        payment_method="momo", notes=f"Pledge payment: {c.name}", recorded_by=staff.id)
                    db.add(donation)
                    db.flush()
                    db.add(PledgePayment(pledge_id=pledge.id, amount=amt, paid_on=paid_on, payment_method="momo",
                                         donation_id=donation.id, recorded_by=staff.id))
                    remaining -= amt
    db.flush()


def seed_care_and_comms(db, staff: User, members: list[Member], groups: dict) -> None:
    active = [m for m in members if m.membership_status == "active"]
    for m in rng.sample(active, k=min(14, len(active))):
        db.add(PastoralLog(member_id=m.id, log_type=rng.choice(["home_visit", "phone_call", "counselling", "hospital_visit"]),
                           notes=rng.choice(["Checked in after missed services.", "Bereavement support for the family.",
                                             "Marriage counselling session.", "Visited at the hospital, recovering well.",
                                             "New baby — arranged a thanksgiving visit."]),
                           status=rng.choice(["open", "open", "completed"]), priority=rng.choice(["normal", "high", "low"]),
                           follow_up_date=TODAY + timedelta(days=rng.randint(-5, 14)), assigned_to=staff.id,
                           logged_by=staff.id, log_date=TODAY - timedelta(days=rng.randint(0, 30))))
    for title, body in [("Harvest Thanksgiving Service", "Our annual harvest is on the last Sunday of the month. Bring your family!"),
                        ("Building project update", "Foundation work is complete. Thank you for your faithful pledges."),
                        ("Youth camp registration", "Registration for the December youth camp is now open at the info desk.")]:
        db.add(Announcement(title=title, body=body, created_by=staff.id))
    for title, days, loc in [("Youth Camp 2026", 24, "Akosombo"), ("Couples' Dinner", 12, "Church Auditorium"),
                             ("Harvest Thanksgiving", 19, "Main Sanctuary"), ("Prayer & Fasting Week", 3, "Main Sanctuary"),
                             ("Men's Breakfast", -6, "Fellowship Hall")]:
        ev = Event(title=title, location=loc, description=f"{title} — all are welcome.", created_by=staff.id,
                   start_datetime=datetime.combine(TODAY + timedelta(days=days), time(9, 0), tzinfo=timezone.utc),
                   max_capacity=rng.choice([None, 80, 150]))
        db.add(ev)
        db.flush()
        for m in rng.sample(active, k=min(len(active), rng.randint(6, 30))):
            db.add(EventRegistration(event_id=ev.id, member_id=m.id))
    db.add(ReminderSchedule(name="Sunday service reminder", message_template="Join us for Sunday service at 8:30am. God bless you!",
                            weekday=5, send_time=time(18, 0), audience_type="active_members", created_by=staff.id))
    if "Choir" in groups:
        db.add(ReminderSchedule(name="Choir rehearsal", message_template="Choir rehearsal Thursday 6pm. Don't miss it!",
                                weekday=3, send_time=time(9, 0), audience_type="department", group_id=groups["Choir"].id,
                                created_by=staff.id))
    for days_ago, body, n in [(2, "Service starts 8:30am tomorrow. Come with a friend!", 160),
                              (9, "Prayer & fasting begins Monday. Join us daily at 6pm.", 158),
                              (16, "Thank you for your generous giving to the building project!", 151)]:
        db.add(Communication(type="sms", body=body, audience_type="active_members", recipient_count=n,
                             successful_count=n - 2, failed_count=2, status="partial", credits_used=n - 2,
                             sent_by=staff.id, sent_at=NOW - timedelta(days=days_ago)))
    db.flush()


def build_grace(db, operator: User) -> None:
    pastor = user(db, "pastor@grace.demo")
    church, admin_membership = create_church(db, name="Grace Covenant Church", slug="grace-covenant", user=pastor,
                                             first_name="Emmanuel", last_name="Asare", phone="0244123456")
    church.address = "12 Lagos Avenue, East Legon, Accra"
    church.phone = "0302 123 456"
    church.website = "https://gracecovenant.example.org"
    church.primary_color = "#1E3A8A"
    church.secondary_color = "#D97706"
    church.denomination = "Charismatic"
    church.sms_sender_id = "GraceCov"
    church.onboarding_completed_at = NOW - timedelta(days=150)
    church.created_at = NOW - timedelta(days=160)
    main = db.query(Branch).filter(Branch.church_id == church.id, Branch.is_main.is_(True)).one()
    main.name = "East Legon (Main)"
    main.address = "12 Lagos Avenue, East Legon"
    tema = Branch(church_id=church.id, name="Tema", address="Community 25, Tema")
    db.add(tema)
    db.flush()

    members = make_members(db, 176, [(main, AREAS_ACCRA), (tema, AREAS_TEMA)])
    groups = seed_groups(db, members)
    sec_m, fin_m, youth_m, tema_m = members[1], members[2], members[3], next(m for m in members if m.home_branch_id == tema.id)
    add_login(db, church, "secretary@grace.demo", "secretary", sec_m)
    add_login(db, church, "finance@grace.demo", "finance", fin_m)
    groups["Youth Ministry"].leader_id = youth_m.id
    db.add(GroupMember(group_id=groups["Youth Ministry"].id, member_id=youth_m.id)) if youth_m.id not in {
        gm.member_id for gm in db.query(GroupMember).filter(GroupMember.group_id == groups["Youth Ministry"].id)} else None
    add_login(db, church, "youth@grace.demo", "group_leader", youth_m)
    add_login(db, church, "tema@grace.demo", "church_admin", tema_m, branch_id=tema.id)

    seed_attendance(db, pastor, members, [main, tema], weeks=16)
    funds = seed_finance(db, pastor, members, [main, tema], weeks=16, scale=1.0)
    seed_outreach(db, church, pastor, members, funds, AREAS_ACCRA, campaign=True)
    seed_care_and_comms(db, pastor, members, groups)

    # Paid Growth plan: a paid invoice and an active subscription.
    church.status = "active"
    church.plan = "growth"
    sub = db.query(Subscription).filter(Subscription.church_id == church.id).one()
    sub.status, sub.plan_code = "active", "growth"
    sub.current_period_start = NOW - timedelta(days=10)
    sub.current_period_end = NOW + timedelta(days=20)
    for months_back, number in ((1, "INV-DEMO-0001"), (0, "INV-DEMO-0002")):
        inv = Invoice(church_id=church.id, number=number, kind="subscription", description="Growth plan (monthly)",
                      plan_code="growth", billing_cycle="monthly", amount=Decimal(199), currency="GHS", status="paid",
                      provider="fake", paid_at=NOW - timedelta(days=10 + 30 * months_back))
        db.add(inv)
        db.flush()
        db.add(Payment(church_id=church.id, invoice_id=inv.id, amount=inv.amount, method="momo", provider="fake"))
    sms_credits.change_balance(db, church.id, 500, "monthly_allowance", reference="INV-DEMO-0002")
    sms_credits.change_balance(db, church.id, -469, "send", reference="Demo SMS history")
    db.add(AuditLog(user_id=pastor.id, action="church_created", table_name="churches", record_id=church.id))
    db.flush()
    print(f"  Grace Covenant Church: {len(members)} members, 2 branches")


def build_living_waters(db) -> None:
    admin = user(db, "admin@livingwaters.demo")
    church, _ = create_church(db, name="Living Waters Assembly", slug="living-waters", user=admin, first_name="Yaw",
                              last_name="Boakye", phone="0277123456")
    church.address = "Bantama High Street, Kumasi"
    church.primary_color = "#0F766E"
    church.secondary_color = "#F59E0B"
    church.onboarding_completed_at = NOW - timedelta(days=5)
    church.trial_ends_at = NOW + timedelta(days=8)
    main = db.query(Branch).filter(Branch.church_id == church.id, Branch.is_main.is_(True)).one()
    main.name = "Bantama"
    members = make_members(db, 46, [(main, AREAS_KSI)])
    # The Grace pastor also helps here (multi-church login).
    add_login(db, church, "pastor@grace.demo", "secretary", members[0])
    seed_attendance(db, admin, members, [main], weeks=6)
    funds = seed_finance(db, admin, members, [main], weeks=6, scale=0.35)
    seed_outreach(db, church, admin, members, funds, AREAS_KSI, campaign=False)
    seed_groups(db, members)
    print(f"  Living Waters Assembly: {len(members)} members (trial)")


def build_bethel(db, operator: User) -> None:
    admin = user(db, "admin@bethel.demo")
    church, _ = create_church(db, name="Bethel Fellowship", slug="bethel-fellowship", user=admin, first_name="Kojo",
                              last_name="Mensah", phone="0201234000")
    main = db.query(Branch).filter(Branch.church_id == church.id, Branch.is_main.is_(True)).one()
    make_members(db, 12, [(main, AREAS_ACCRA)])
    church.status = "suspended"
    church.suspended_reason = "Suspended at the church's request while they migrate records."
    church.settings = {"status_before_suspension": "trialing"}
    print("  Bethel Fellowship: suspended")


def reset_database(db) -> None:
    url = make_url(settings.DATABASE_URL)
    if url.host not in ("localhost", "127.0.0.1"):
        sys.exit(f"Refusing to --reset a non-local database ({url.host}).")
    tables = [r[0] for r in db.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename NOT IN ('alembic_version', 'plans')"
    ))]
    db.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " CASCADE"))
    db.commit()
    print("Database wiped (plans kept).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="wipe all data first (local database only)")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.reset:
            reset_database(db)
        operator = user(db, "owner@asafo.demo", platform_admin=True)
        db.commit()
        for slug, build in (("grace-covenant", lambda: build_grace(db, operator)),
                            ("living-waters", lambda: build_living_waters(db)),
                            ("bethel-fellowship", lambda: build_bethel(db, operator))):
            clear_tenant(db)
            if db.query(Church).filter(Church.slug == slug).first():
                print(f"  {slug} already exists, skipping (use --reset to rebuild)")
                continue
            build()
            db.commit()
        clear_tenant(db)
        print(f"\nDone. Sign in with any demo login; password: {PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
