from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.member import Member
from app.models.membership import Membership
from app.models.pastoral import PastoralLog
from app.models.user import User
from app.schemas.pastoral import PastoralLogCreate, PastoralLogUpdate


def due_state(follow_up_date: date | None, status: str, today: date | None = None) -> str:
    if status == "completed":
        return "completed"
    if not follow_up_date:
        return "unscheduled"
    today = today or date.today()
    if follow_up_date < today:
        return "overdue"
    if follow_up_date == today:
        return "due_today"
    return "upcoming"


def list_logs(
    db: Session,
    member_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
) -> list[PastoralLog]:
    query = db.query(PastoralLog).options(
        joinedload(PastoralLog.member),
        joinedload(PastoralLog.assignee),
    )
    if member_id:
        query = query.filter(PastoralLog.member_id == member_id)
    if status:
        query = query.filter(PastoralLog.status == status)
    if priority:
        query = query.filter(PastoralLog.priority == priority)
    if assigned_to:
        query = query.filter(PastoralLog.assigned_to == assigned_to)
    priority_order = case(
        (PastoralLog.priority == "urgent", 0),
        (PastoralLog.priority == "high", 1),
        (PastoralLog.priority == "normal", 2),
        else_=3,
    )
    return query.order_by(
        case((PastoralLog.status == "open", 0), else_=1),
        PastoralLog.follow_up_date.asc().nullslast(),
        priority_order,
        PastoralLog.created_at.desc(),
    ).all()


def get_log(db: Session, log_id: UUID) -> PastoralLog | None:
    return db.query(PastoralLog).filter(PastoralLog.id == log_id).first()


def create_log(db: Session, payload: PastoralLogCreate, logged_by: UUID | None) -> PastoralLog:
    data = payload.model_dump()
    if not data.get("assigned_to"):
        data["assigned_to"] = logged_by
    row = PastoralLog(**data, logged_by=logged_by)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_log(db: Session, log_id: UUID, payload: PastoralLogUpdate) -> PastoralLog | None:
    row = get_log(db, log_id)
    if not row:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("status") == "completed" and row.status != "completed":
        updates["completed_at"] = datetime.now(timezone.utc)
    elif updates.get("status") == "open" and row.status == "completed":
        updates["completed_at"] = None
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


ASSIGNEE_ROLES = ["church_admin", "secretary", "group_leader"]


def list_assignees(db: Session, church_id: UUID):
    """Active staff of THIS church who can own a care plan. Rows expose ``id``, ``email``, ``role``
    (the role is the user's membership role in the church)."""
    return (
        db.query(User.id, User.email, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .filter(
            Membership.church_id == church_id,
            Membership.is_active.is_(True),
            Membership.role.in_(ASSIGNEE_ROLES),
            User.is_active.is_(True),
        )
        .order_by(User.email.asc())
        .all()
    )


def summary(db: Session, assigned_to: UUID | None = None) -> dict:
    today = date.today()
    query = db.query(PastoralLog)
    if assigned_to:
        query = query.filter(PastoralLog.assigned_to == assigned_to)
    rows = query.all()
    return {
        "open": sum(row.status == "open" for row in rows),
        "overdue": sum(due_state(row.follow_up_date, row.status, today) == "overdue" for row in rows),
        "due_today": sum(due_state(row.follow_up_date, row.status, today) == "due_today" for row in rows),
        "completed": sum(row.status == "completed" for row in rows),
    }


def list_attendance_risks(db: Session, limit: int = 25) -> list[dict]:
    cutoff = date.today() - timedelta(days=30)
    last_present = (
        db.query(
            AttendanceRecord.member_id.label("member_id"),
            func.max(AttendanceSession.session_date).label("last_present_date"),
        )
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .filter(AttendanceRecord.status == "present")
        .group_by(AttendanceRecord.member_id)
        .subquery()
    )
    open_followups = (
        db.query(PastoralLog.member_id)
        .filter(PastoralLog.status == "open")
        .subquery()
    )
    rows = (
        db.query(Member, last_present.c.last_present_date)
        .outerjoin(last_present, last_present.c.member_id == Member.id)
        .outerjoin(open_followups, open_followups.c.member_id == Member.id)
        .filter(
            open_followups.c.member_id.is_(None),
            Member.membership_status.in_(["active", "inactive", "visitor", "new_convert"]),
        )
        .order_by(last_present.c.last_present_date.asc().nullsfirst(), Member.last_name.asc())
        .all()
    )

    risks = []
    for member, last_present_date in rows:
        if member.membership_status == "inactive":
            reason = "Membership status is inactive"
        elif last_present_date and last_present_date <= cutoff:
            reason = f"No recorded attendance since {last_present_date.isoformat()}"
        elif last_present_date is None:
            reference_date = member.date_joined or (member.created_at.date() if member.created_at else date.today())
            if reference_date > cutoff:
                continue
            reason = "No recorded attendance in the past 30 days"
        else:
            continue

        risks.append({
            "member_id": member.id,
            "member_name": f"{member.first_name} {member.last_name}".strip(),
            "membership_status": member.membership_status,
            "phone": member.phone,
            "last_present_date": last_present_date,
            "reason": reason,
        })
        if len(risks) >= limit:
            break
    return risks
