from calendar import month_abbr
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.donation import Donation, Expense
from app.models.communication import Communication, ReminderSchedule
from app.models.event import Event
from app.models.group import Group, GroupMember
from app.models.member import Member
from app.models.pastoral import PastoralLog


def _month_start(dt: date) -> date:
    return date(dt.year, dt.month, 1)


def _add_months(dt: date, months: int) -> date:
    year = dt.year + ((dt.month - 1 + months) // 12)
    month = ((dt.month - 1 + months) % 12) + 1
    return date(year, month, 1)


def _month_label(dt: date) -> str:
    return f"{month_abbr[dt.month]} {str(dt.year)[-2:]}"


def _low_attendance_count(db: Session) -> int:
    cutoff = date.today() - timedelta(days=30)

    rows = (
        db.query(
            Member.id.label("member_id"),
            func.max(AttendanceSession.session_date).label("last_present_date"),
        )
        .outerjoin(AttendanceRecord, AttendanceRecord.member_id == Member.id)
        .outerjoin(
            AttendanceSession,
            and_(
                AttendanceSession.id == AttendanceRecord.session_id,
                AttendanceRecord.status == "present",
            ),
        )
        .filter(Member.membership_status == "active")
        .group_by(Member.id)
        .all()
    )

    return sum(1 for row in rows if row.last_present_date is None or row.last_present_date <= cutoff)


def get_dashboard_stats(db: Session, pastoral_assigned_to: UUID | None = None) -> dict:
    today = date.today()
    month_start = _month_start(today)

    total_members = db.query(func.count(Member.id)).filter(Member.membership_status == "active").scalar() or 0
    new_members_this_month = (
        db.query(func.count(Member.id))
        .filter(Member.date_joined.isnot(None), Member.date_joined >= month_start)
        .scalar()
        or 0
    )

    last_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    present_last_sunday = (
        db.query(func.count(AttendanceRecord.id))
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .filter(AttendanceSession.session_date == last_sunday, AttendanceRecord.status == "present")
        .scalar()
        or 0
    )

    if present_last_sunday == 0:
        latest_session_date = db.query(func.max(AttendanceSession.session_date)).scalar()
        if latest_session_date:
            present_last_sunday = (
                db.query(func.count(AttendanceRecord.id))
                .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
                .filter(AttendanceSession.session_date == latest_session_date, AttendanceRecord.status == "present")
                .scalar()
                or 0
            )

    attendance_percentage = round((present_last_sunday / total_members) * 100, 2) if total_members else 0

    donations_this_month = (
        db.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(
            extract("year", Donation.donation_date) == today.year,
            extract("month", Donation.donation_date) == today.month,
        )
        .scalar()
        or 0
    )
    donations_this_year = (
        db.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(extract("year", Donation.donation_date) == today.year)
        .scalar()
        or 0
    )
    expenses_this_month = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            extract("year", Expense.expense_date) == today.year,
            extract("month", Expense.expense_date) == today.month,
        )
        .scalar()
        or 0
    )
    expenses_this_year = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(extract("year", Expense.expense_date) == today.year)
        .scalar()
        or 0
    )

    upcoming_event_rows = (
        db.query(Event)
        .filter(Event.start_datetime >= func.now())
        .order_by(Event.start_datetime.asc())
        .limit(5)
        .all()
    )
    department_rows = []
    for group in db.query(Group).filter(Group.is_active.is_(True)).order_by(Group.name.asc()).all():
        member_count = (
            db.query(func.count(GroupMember.id))
            .join(Member, Member.id == GroupMember.member_id)
            .filter(GroupMember.group_id == group.id, Member.membership_status == "active")
            .scalar()
            or 0
        )
        department_rows.append({
            "id": group.id,
            "name": group.name,
            "member_count": int(member_count),
            "leader_name": f"{group.leader.first_name} {group.leader.last_name}".strip() if group.leader else None,
        })

    sms_year = today.year
    sms_month = today.month
    sms_rows = (
        db.query(
            func.coalesce(func.sum(Communication.successful_count), 0).label("successful"),
            func.coalesce(func.sum(Communication.failed_count), 0).label("failed"),
        )
        .filter(
            Communication.type == "sms",
            extract("year", Communication.sent_at) == sms_year,
            extract("month", Communication.sent_at) == sms_month,
        )
        .first()
    )
    pastoral_scope = []
    if pastoral_assigned_to:
        pastoral_scope.append(PastoralLog.assigned_to == pastoral_assigned_to)
    open_followups = (
        db.query(func.count(PastoralLog.id))
        .filter(PastoralLog.status == "open", *pastoral_scope)
        .scalar()
        or 0
    )
    overdue_followups = (
        db.query(func.count(PastoralLog.id))
        .filter(
            PastoralLog.status == "open",
            PastoralLog.follow_up_date.isnot(None),
            PastoralLog.follow_up_date < today,
            *pastoral_scope,
        )
        .scalar()
        or 0
    )
    due_today_followups = (
        db.query(func.count(PastoralLog.id))
        .filter(
            PastoralLog.status == "open",
            PastoralLog.follow_up_date == today,
            *pastoral_scope,
        )
        .scalar()
        or 0
    )

    return {
        "total_members": total_members,
        "active_members": total_members,
        "visitors": db.query(func.count(Member.id)).filter(Member.membership_status == "visitor").scalar() or 0,
        "new_converts": db.query(func.count(Member.id)).filter(Member.membership_status == "new_convert").scalar() or 0,
        "new_members_this_month": new_members_this_month,
        "attendance_last_sunday": present_last_sunday,
        "attendance_percentage": attendance_percentage,
        "donations_this_month": float(donations_this_month),
        "donations_this_year": float(donations_this_year),
        "expenses_this_month": float(expenses_this_month),
        "expenses_this_year": float(expenses_this_year),
        "net_flow_this_month": float(donations_this_month) - float(expenses_this_month),
        "low_attendance_members": _low_attendance_count(db),
        "upcoming_events": db.query(func.count(Event.id)).filter(Event.start_datetime >= func.now()).scalar() or 0,
        "upcoming_event_list": [
            {"id": event.id, "title": event.title, "start_datetime": event.start_datetime, "location": event.location}
            for event in upcoming_event_rows
        ],
        "departments": department_rows,
        "department_count": len(department_rows),
        "sms_sent_this_month": int(sms_rows.successful or 0),
        "sms_failed_this_month": int(sms_rows.failed or 0),
        "active_reminders": db.query(func.count(ReminderSchedule.id)).filter(ReminderSchedule.is_active.is_(True)).scalar() or 0,
        "open_pastoral_followups": int(open_followups),
        "overdue_pastoral_followups": int(overdue_followups),
        "pastoral_followups_due_today": int(due_today_followups),
    }


def get_attendance_monthly(db: Session, months: int = 6) -> list[dict]:
    today = date.today()
    start = _add_months(_month_start(today), -(months - 1))

    rows = (
        db.query(
            func.date_trunc("month", AttendanceSession.session_date).label("month"),
            func.count(AttendanceRecord.id).label("present_count"),
        )
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .filter(AttendanceRecord.status == "present", AttendanceSession.session_date >= start)
        .group_by(func.date_trunc("month", AttendanceSession.session_date))
        .all()
    )

    row_map = {date(r.month.year, r.month.month, 1): int(r.present_count) for r in rows}

    data = []
    for i in range(months):
        month = _add_months(start, i)
        data.append({"month": _month_label(month), "value": row_map.get(month, 0)})
    return data


def get_members_growth(db: Session, months: int = 6) -> list[dict]:
    today = date.today()
    start = _add_months(_month_start(today), -(months - 1))

    data = []
    running_total = (
        db.query(func.count(Member.id))
        .filter(Member.date_joined.isnot(None), Member.date_joined < start)
        .scalar()
        or 0
    )

    for i in range(months):
        month_start = _add_months(start, i)
        next_month = _add_months(month_start, 1)
        added = (
            db.query(func.count(Member.id))
            .filter(Member.date_joined.isnot(None), Member.date_joined >= month_start, Member.date_joined < next_month)
            .scalar()
            or 0
        )
        running_total += added
        data.append({"month": _month_label(month_start), "value": int(running_total)})

    return data


def get_donations_monthly(db: Session, months: int = 6) -> list[dict]:
    today = date.today()
    start = _add_months(_month_start(today), -(months - 1))

    rows = (
        db.query(
            func.date_trunc("month", Donation.donation_date).label("month"),
            func.coalesce(func.sum(Donation.amount), 0).label("total_amount"),
        )
        .filter(Donation.donation_date >= start)
        .group_by(func.date_trunc("month", Donation.donation_date))
        .all()
    )

    row_map = {date(r.month.year, r.month.month, 1): float(r.total_amount) for r in rows}

    data = []
    for i in range(months):
        month = _add_months(start, i)
        data.append({"month": _month_label(month), "value": row_map.get(month, 0)})
    return data


def get_expenses_monthly(db: Session, months: int = 6) -> list[dict]:
    today = date.today()
    start = _add_months(_month_start(today), -(months - 1))

    rows = (
        db.query(
            func.date_trunc("month", Expense.expense_date).label("month"),
            func.coalesce(func.sum(Expense.amount), 0).label("total_amount"),
        )
        .filter(Expense.expense_date >= start)
        .group_by(func.date_trunc("month", Expense.expense_date))
        .all()
    )

    row_map = {date(r.month.year, r.month.month, 1): float(r.total_amount) for r in rows}

    data = []
    for i in range(months):
        month = _add_months(start, i)
        data.append({"month": _month_label(month), "value": row_map.get(month, 0)})
    return data
