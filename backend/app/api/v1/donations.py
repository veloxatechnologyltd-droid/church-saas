import csv
import io
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.crud import donation as donation_crud
from app.db.database import get_db
from app.schemas.donation import (
    DonationCreate,
    DonationFundCreate,
    DonationFundResponse,
    DonationResponse,
    ExpenseCategoryCreate,
    ExpenseCategoryResponse,
    ExpenseCreate,
    ExpenseResponse,
    FinanceBatchCreate,
    FinanceBatchResponse,
)
from app.services.audit import record_audit

router = APIRouter()


def serialize_donation(row) -> dict:
    data = DonationResponse.model_validate(row).model_dump()
    data["fund_name"] = row.fund.name if row.fund else None
    data["batch_title"] = row.batch.title if row.batch else None
    data["member_name"] = f"{row.member.first_name} {row.member.last_name}" if row.member else None
    return data


def serialize_expense(row) -> dict:
    data = ExpenseResponse.model_validate(row).model_dump()
    data["category_name"] = row.category.name if row.category else None
    return data


@router.get("/")
def list_donations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    batch_id: UUID | None = Query(default=None),
    fund_id: UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    rows, total = donation_crud.list_donations(
        db,
        skip=skip,
        limit=limit,
        batch_id=batch_id,
        fund_id=fund_id,
        start_date=start_date,
        end_date=end_date,
    )
    page = (skip // limit) + 1
    return {"status": "success", "data": [serialize_donation(row) for row in rows], "total": total, "page": page, "limit": limit}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_donation(
    payload: DonationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    try:
        row = donation_crud.create_donation(db, payload, recorded_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(db, user_id=current_user.id, action="created", table_name="donations", record_id=row.id, new_value={"amount": str(row.amount), "fund_id": str(row.fund_id)})
    db.commit()
    return {"status": "success", "data": serialize_donation(row)}


@router.get("/funds")
def list_funds(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = donation_crud.list_funds(db)
    return {"status": "success", "data": [DonationFundResponse.model_validate(row).model_dump() for row in rows]}


@router.post("/funds/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_funds(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    rows = donation_crud.bootstrap_standard_funds(db)
    return {"status": "success", "data": [DonationFundResponse.model_validate(row).model_dump() for row in rows]}


@router.post("/funds", status_code=status.HTTP_201_CREATED)
def create_fund(
    payload: DonationFundCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    row = donation_crud.create_fund(db, payload)
    record_audit(db, user_id=current_user.id, action="created", table_name="donation_funds", record_id=row.id, new_value={"name": row.name})
    db.commit()
    return {"status": "success", "data": DonationFundResponse.model_validate(row).model_dump()}


@router.get("/batches")
def list_batches(
    include_closed: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    rows = donation_crud.list_batches(db, include_closed=include_closed)
    return {"status": "success", "data": [FinanceBatchResponse.model_validate(row).model_dump() for row in rows]}


@router.post("/batches", status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: FinanceBatchCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    row = donation_crud.create_batch(db, payload, recorded_by=current_user.id)
    record_audit(db, user_id=current_user.id, action="created", table_name="finance_batches", record_id=row.id, new_value={"title": row.title, "service_date": row.service_date.isoformat()})
    db.commit()
    data = FinanceBatchResponse.model_validate(row).model_dump()
    data["total_amount"] = 0
    data["transaction_count"] = 0
    return {"status": "success", "data": data}


@router.post("/batches/{batch_id}/close")
def close_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    try:
        row = donation_crud.close_batch(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit(
        db,
        user_id=current_user.id,
        action="closed",
        table_name="finance_batches",
        record_id=row.id,
        new_value={"title": row.title, "is_closed": True},
    )
    db.commit()
    return {"status": "success", "data": FinanceBatchResponse.model_validate(row).model_dump()}


@router.get("/member/{member_id}")
def get_member_history(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in {"church_admin", "finance"} and str(current_user.member_id) != str(member_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.crud.member import get_member

    if not get_member(db, member_id):
        raise HTTPException(status_code=404, detail="Member not found")
    rows = donation_crud.member_history(db, member_id)
    return {"status": "success", "data": [serialize_donation(row) for row in rows]}


@router.get("/reports/monthly")
def monthly_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    fund_id: UUID | None = Query(default=None),
    batch_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    return {"status": "success", "data": donation_crud.monthly_report(db, year=year, start_date=start_date, end_date=end_date, fund_id=fund_id, batch_id=batch_id)}


@router.get("/reports/expenses/monthly")
def monthly_expense_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    return {"status": "success", "data": donation_crud.monthly_expense_report(db, year=year, start_date=start_date, end_date=end_date, category_id=category_id)}


@router.get("/expenses")
def list_expenses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    category_id: UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    rows, total = donation_crud.list_expenses(
        db,
        skip=skip,
        limit=limit,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
    )
    page = (skip // limit) + 1
    return {"status": "success", "data": [serialize_expense(row) for row in rows], "total": total, "page": page, "limit": limit}


@router.get("/summary")
def get_finance_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    batch_id: UUID | None = Query(default=None),
    fund_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    data = donation_crud.finance_summary(
        db,
        start_date=start_date,
        end_date=end_date,
        batch_id=batch_id,
        fund_id=fund_id,
        category_id=category_id,
    )
    return {"status": "success", "data": data}


@router.get("/export/summary")
def export_finance_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    batch_id: UUID | None = Query(default=None),
    fund_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    summary = donation_crud.finance_summary(
        db,
        start_date=start_date,
        end_date=end_date,
        batch_id=batch_id,
        fund_id=fund_id,
        category_id=category_id,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "name", "amount"])
    writer.writerow(["totals", "income_total", summary["income_total"]])
    writer.writerow(["totals", "expense_total", summary["expense_total"]])
    writer.writerow(["totals", "net_total", summary["net_total"]])
    for row in summary["income_by_fund"]:
        writer.writerow(["income_by_fund", row["name"], row["value"]])
    for row in summary["expenses_by_category"]:
        writer.writerow(["expenses_by_category", row["name"], row["value"]])

    headers = {"Content-Disposition": "attachment; filename=finance-summary.csv"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    row = donation_crud.create_expense(db, payload, recorded_by=current_user.id)
    record_audit(db, user_id=current_user.id, action="created", table_name="expenses", record_id=row.id, new_value={"amount": str(row.amount), "category_id": str(row.category_id)})
    db.commit()
    return {"status": "success", "data": serialize_expense(row)}


@router.get("/expense-categories")
def list_expense_categories(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = donation_crud.list_expense_categories(db)
    return {"status": "success", "data": [ExpenseCategoryResponse.model_validate(row).model_dump() for row in rows]}


@router.post("/expense-categories/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_expense_categories(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    rows = donation_crud.bootstrap_expense_categories(db)
    return {"status": "success", "data": [ExpenseCategoryResponse.model_validate(row).model_dump() for row in rows]}


@router.post("/expense-categories", status_code=status.HTTP_201_CREATED)
def create_expense_category(
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin")),
):
    row = donation_crud.create_expense_category(db, payload)
    record_audit(db, user_id=current_user.id, action="created", table_name="expense_categories", record_id=row.id, new_value={"name": row.name})
    db.commit()
    return {"status": "success", "data": ExpenseCategoryResponse.model_validate(row).model_dump()}


@router.get("/reports/annual")
def annual_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    fund_id: UUID | None = Query(default=None),
    batch_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    return {"status": "success", "data": donation_crud.annual_report(db, year=year, start_date=start_date, end_date=end_date, fund_id=fund_id, batch_id=batch_id)}


@router.get("/member/{member_id}/statement")
def member_statement(
    member_id: UUID,
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    """Contribution statement for one member (optionally one calendar year), with
    per-fund totals and the church's details, ready to print or send."""
    from app.crud.member import get_member

    member = get_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    rows = donation_crud.member_history(db, member_id)
    if year:
        rows = [row for row in rows if row.donation_date and row.donation_date.year == year]
    total = sum(float(row.amount) for row in rows)
    by_fund: dict[str, float] = {}
    for row in rows:
        name = row.fund.name if row.fund else "Other"
        by_fund[name] = by_fund.get(name, 0.0) + float(row.amount)
    church = current_user.church
    return {
        "status": "success",
        "data": {
            "member_id": member_id,
            "member_name": f"{member.first_name} {member.last_name}",
            "member_phone": member.phone,
            "member_address": member.address,
            "church": {"name": church.name, "address": church.address, "phone": church.phone,
                       "email": church.email, "logo_url": church.logo_url, "currency": church.currency},
            "year": year,
            "generated_on": date.today().isoformat(),
            "total": total,
            "by_fund": [{"fund": k, "total": v} for k, v in sorted(by_fund.items(), key=lambda kv: -kv[1])],
            "items": [serialize_donation(row) for row in rows],
        },
    }


@router.get("/{donation_id}")
def get_donation(
    donation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("church_admin", "finance")),
):
    row = donation_crud.get_donation(db, donation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Donation not found")
    return {"status": "success", "data": serialize_donation(row)}
