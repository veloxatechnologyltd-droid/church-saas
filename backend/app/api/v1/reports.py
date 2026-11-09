import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.crud import reports as reports_crud
from app.crud import donation as donation_crud
from app.crud import member as member_crud
from app.db.database import get_db
from app.core.dependencies import require_roles
from app.models.donation import Donation

router = APIRouter()


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    pastoral_assigned_to = current_user.id if current_user.role == "group_leader" else None
    data = reports_crud.get_dashboard_stats(db, pastoral_assigned_to=pastoral_assigned_to)
    return {"status": "success", "data": data}


@router.get("/attendance/monthly")
def attendance_monthly(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = reports_crud.get_attendance_monthly(db, months=6)
    return {"status": "success", "data": data}


@router.get("/donations/monthly")
def donations_monthly(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = reports_crud.get_donations_monthly(db, months=6)
    return {"status": "success", "data": data}


@router.get("/expenses/monthly")
def expenses_monthly(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = reports_crud.get_expenses_monthly(db, months=6)
    return {"status": "success", "data": data}


@router.get("/members/growth")
def members_growth(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = reports_crud.get_members_growth(db, months=6)
    return {"status": "success", "data": data}


@router.get("/export/members")
def export_members_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("superadmin", "secretary")),
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
    current_user=Depends(require_roles("superadmin", "finance")),
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
