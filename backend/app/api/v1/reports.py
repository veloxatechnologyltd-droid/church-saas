import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import PEOPLE_ROLES, REPORT_ROLES, require_roles
from app.crud import reports as reports_crud
from app.crud import donation as donation_crud
from app.crud import member as member_crud
from app.db.database import get_db
from app.models.donation import Donation

router = APIRouter()


# Money figures on the dashboard are for the roles that can open Reports (admin, finance, secretary).
_MONEY_KEYS = ("donations_this_month", "donations_this_year", "expenses_this_month", "expenses_this_year", "net_flow_this_month")
# A plain church member only gets what is public inside the church: upcoming events.
_MEMBER_DASHBOARD_KEYS = ("upcoming_events", "upcoming_event_list")


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user=Depends(require_roles(*PEOPLE_ROLES, "member"))):
    pastoral_assigned_to = current_user.id if current_user.role == "group_leader" else None
    data = reports_crud.get_dashboard_stats(db, pastoral_assigned_to=pastoral_assigned_to)
    if current_user.role == "member":
        data = {key: data[key] for key in _MEMBER_DASHBOARD_KEYS if key in data}
    elif current_user.role not in REPORT_ROLES:
        data = {key: value for key, value in data.items() if key not in _MONEY_KEYS}
    return {"status": "success", "data": data}


@router.get("/attendance/monthly")
def attendance_monthly(db: Session = Depends(get_db), current_user=Depends(require_roles(*PEOPLE_ROLES))):
    data = reports_crud.get_attendance_monthly(db, months=6)
    return {"status": "success", "data": data}


@router.get("/donations/monthly")
def donations_monthly(db: Session = Depends(get_db), current_user=Depends(require_roles(*REPORT_ROLES))):
    data = reports_crud.get_donations_monthly(db, months=6)
    return {"status": "success", "data": data}


@router.get("/expenses/monthly")
def expenses_monthly(db: Session = Depends(get_db), current_user=Depends(require_roles(*REPORT_ROLES))):
    data = reports_crud.get_expenses_monthly(db, months=6)
    return {"status": "success", "data": data}


@router.get("/members/growth")
def members_growth(db: Session = Depends(get_db), current_user=Depends(require_roles(*PEOPLE_ROLES))):
    data = reports_crud.get_members_growth(db, months=6)
    return {"status": "success", "data": data}


@router.get("/export/members")
def export_members_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "secretary")),
):
    members, _ = member_crud.get_members(db, skip=0, limit=100000)
    csv_data = member_crud.generate_members_csv(members)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=members-report.csv"},
    )


@router.get("/export/donations")
def export_donations_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    rows = donation_crud.list_donations(db, skip=0, limit=100000)[0]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "member", "fund", "amount", "currency", "payment_method", "reference"])
    for row in rows:
        writer.writerow([
            row.donation_date,
            f"{row.member.first_name} {row.member.last_name}".strip() if row.member else "Anonymous",
            row.fund.name if row.fund else "",
            row.amount,
            row.currency,
            row.payment_method or "",
            row.reference or "",
        ])
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance-report.csv"},
    )
