from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models.donation import Donation, DonationFund, Expense, ExpenseCategory, FinanceBatch
from app.schemas.donation import DonationCreate, DonationFundCreate, ExpenseCategoryCreate, ExpenseCreate, FinanceBatchCreate


STANDARD_FUNDS = [
    {"name": "Tithe", "code": "tithe", "description": "Regular member tithe contributions.", "requires_member": True},
    {"name": "Offering", "code": "offering", "description": "General service offertory and loose collections.", "requires_member": False},
    {"name": "Harvest", "code": "harvest", "description": "Annual harvest and thanksgiving campaign giving.", "requires_member": False},
    {"name": "Thanksgiving", "code": "thanksgiving", "description": "Special thanksgiving offerings.", "requires_member": False},
    {"name": "Missions", "code": "missions", "description": "Mission support and outreach giving.", "requires_member": False},
    {"name": "Welfare", "code": "welfare", "description": "Member care and benevolence support fund.", "requires_member": False},
    {"name": "Building Fund", "code": "building_fund", "description": "Church building, renovation, and capital projects.", "requires_member": False},
    {"name": "Seed", "code": "seed", "description": "Special seed and prophetic giving.", "requires_member": False},
]

STANDARD_EXPENSE_CATEGORIES = [
    {"name": "Utilities", "description": "Power, water, internet, and recurring facility bills."},
    {"name": "Welfare", "description": "Member welfare, benevolence, and support spending."},
    {"name": "Missions", "description": "Mission work, outreach, and evangelism spending."},
    {"name": "Maintenance", "description": "Church equipment, facility repairs, and upkeep."},
    {"name": "Programs", "description": "Program logistics, events, and service materials."},
    {"name": "Payroll", "description": "Staff, stipends, and ministry honorarium payments."},
]


def _apply_donation_filters(query, batch_id: UUID | None = None, fund_id: UUID | None = None, start_date: date | None = None, end_date: date | None = None):
    if batch_id:
        query = query.filter(Donation.batch_id == batch_id)
    if fund_id:
        query = query.filter(Donation.fund_id == fund_id)
    if start_date:
        query = query.filter(Donation.donation_date >= start_date)
    if end_date:
        query = query.filter(Donation.donation_date <= end_date)
    return query


def _apply_expense_filters(query, category_id: UUID | None = None, start_date: date | None = None, end_date: date | None = None):
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    return query


def list_donations(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    batch_id: UUID | None = None,
    fund_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[Donation], int]:
    query = db.query(Donation)
    query = _apply_donation_filters(query, batch_id=batch_id, fund_id=fund_id, start_date=start_date, end_date=end_date)
    total = query.count()
    rows = query.order_by(Donation.donation_date.desc(), Donation.created_at.desc()).offset(skip).limit(limit).all()
    return rows, total


def get_donation(db: Session, donation_id: UUID) -> Donation | None:
    return db.query(Donation).filter(Donation.id == donation_id).first()


def create_donation(db: Session, payload: DonationCreate, recorded_by: UUID | None) -> Donation:
    fund = db.query(DonationFund).filter(DonationFund.id == payload.fund_id).first()
    if not fund:
        raise ValueError("Selected finance fund does not exist")
    if fund.requires_member and not payload.member_id:
        raise ValueError(f"{fund.name} entries must be linked to a member")
    if payload.batch_id:
        batch = db.query(FinanceBatch).filter(FinanceBatch.id == payload.batch_id).first()
        if not batch:
            raise ValueError("Selected service collection does not exist")
        if batch.is_closed:
            raise ValueError("This service collection is closed and cannot accept new entries")

    donation = Donation(**payload.model_dump(), recorded_by=recorded_by)
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return donation


def list_funds(db: Session) -> list[DonationFund]:
    return db.query(DonationFund).order_by(DonationFund.name.asc()).all()


def create_fund(db: Session, payload: DonationFundCreate) -> DonationFund:
    existing = db.query(DonationFund).filter(func.lower(DonationFund.name) == payload.name.strip().lower()).first()
    if existing:
        return existing
    fund = DonationFund(
        name=payload.name.strip(),
        code=payload.code.strip().lower() if payload.code else None,
        description=payload.description,
        requires_member=payload.requires_member,
    )
    db.add(fund)
    db.commit()
    db.refresh(fund)
    return fund


def bootstrap_standard_funds(db: Session) -> list[DonationFund]:
    existing_names = {row.name.lower() for row in db.query(DonationFund).all()}
    created = []
    for item in STANDARD_FUNDS:
        if item["name"].lower() in existing_names:
            row = db.query(DonationFund).filter(func.lower(DonationFund.name) == item["name"].lower()).first()
            if row:
                row.code = item["code"]
                row.description = row.description or item["description"]
                row.requires_member = item["requires_member"]
            continue
        fund = DonationFund(**item)
        db.add(fund)
        created.append(fund)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def list_batches(db: Session, include_closed: bool = True) -> list[dict]:
    total_amount = func.coalesce(func.sum(Donation.amount), Decimal("0.00"))
    transaction_count = func.count(Donation.id)
    query = (
        db.query(
            FinanceBatch,
            total_amount.label("total_amount"),
            transaction_count.label("transaction_count"),
        )
        .outerjoin(Donation, Donation.batch_id == FinanceBatch.id)
        .group_by(FinanceBatch.id)
        .order_by(FinanceBatch.service_date.desc(), FinanceBatch.created_at.desc())
    )
    if not include_closed:
        query = query.filter(FinanceBatch.is_closed.is_(False))
    rows = query.all()
    return [
        {
            "id": batch.id,
            "title": batch.title,
            "service_date": batch.service_date,
            "service_type": batch.service_type,
            "notes": batch.notes,
            "is_closed": batch.is_closed,
            "recorded_by": batch.recorded_by,
            "created_at": batch.created_at,
            "total_amount": total_amount or Decimal("0.00"),
            "transaction_count": int(transaction_count or 0),
        }
        for batch, total_amount, transaction_count in rows
    ]


def create_batch(db: Session, payload: FinanceBatchCreate, recorded_by: UUID | None) -> FinanceBatch:
    batch = FinanceBatch(**payload.model_dump(), recorded_by=recorded_by)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def close_batch(db: Session, batch_id: UUID) -> FinanceBatch:
    batch = db.query(FinanceBatch).filter(FinanceBatch.id == batch_id).first()
    if not batch:
        raise ValueError("Selected service collection does not exist")
    if batch.is_closed:
        return batch
    batch.is_closed = True
    db.commit()
    db.refresh(batch)
    return batch


def member_history(db: Session, member_id: UUID) -> list[Donation]:
    return (
        db.query(Donation)
        .filter(Donation.member_id == member_id)
        .order_by(Donation.donation_date.desc(), Donation.created_at.desc())
        .all()
    )


def monthly_report(
    db: Session,
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    fund_id: UUID | None = None,
    batch_id: UUID | None = None,
) -> list[dict]:
    year = year or date.today().year
    query = db.query(
        extract("month", Donation.donation_date).label("month"),
        func.coalesce(func.sum(Donation.amount), 0).label("total_amount"),
    ).filter(extract("year", Donation.donation_date) == year)
    query = _apply_donation_filters(query, batch_id=batch_id, fund_id=fund_id, start_date=start_date, end_date=end_date)
    rows = (
        query
        .group_by(extract("month", Donation.donation_date))
        .order_by(extract("month", Donation.donation_date))
        .all()
    )
    return [{"month": int(row.month), "value": float(row.total_amount)} for row in rows]


def annual_report(
    db: Session,
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    fund_id: UUID | None = None,
    batch_id: UUID | None = None,
) -> dict:
    year = year or date.today().year
    donation_query = _apply_donation_filters(
        db.query(Donation),
        batch_id=batch_id,
        fund_id=fund_id,
        start_date=start_date,
        end_date=end_date,
    ).filter(extract("year", Donation.donation_date) == year)
    total = donation_query.with_entities(func.coalesce(func.sum(Donation.amount), Decimal("0.00"))).scalar()
    by_fund_query = (
        db.query(DonationFund.name, func.coalesce(func.sum(Donation.amount), 0).label("total_amount"))
        .join(Donation, Donation.fund_id == DonationFund.id)
        .filter(extract("year", Donation.donation_date) == year)
    )
    by_fund_query = _apply_donation_filters(by_fund_query, batch_id=batch_id, fund_id=fund_id, start_date=start_date, end_date=end_date)
    by_fund = by_fund_query.group_by(DonationFund.name).order_by(DonationFund.name.asc()).all()
    return {
        "year": year,
        "total": float(total or 0),
        "funds": [{"fund": row.name, "value": float(row.total_amount)} for row in by_fund],
    }


def donation_totals(db: Session) -> dict:
    today = date.today()
    month_total = (
        db.query(func.coalesce(func.sum(Donation.amount), Decimal("0.00")))
        .filter(
            extract("year", Donation.donation_date) == today.year,
            extract("month", Donation.donation_date) == today.month,
        )
        .scalar()
    )
    year_total = (
        db.query(func.coalesce(func.sum(Donation.amount), Decimal("0.00")))
        .filter(extract("year", Donation.donation_date) == today.year)
        .scalar()
    )
    return {
        "donations_this_month": float(month_total or 0),
        "donations_this_year": float(year_total or 0),
    }


def list_expense_categories(db: Session) -> list[ExpenseCategory]:
    return db.query(ExpenseCategory).order_by(ExpenseCategory.name.asc()).all()


def bootstrap_expense_categories(db: Session) -> list[ExpenseCategory]:
    existing_names = {row.name.lower() for row in db.query(ExpenseCategory).all()}
    created = []
    for item in STANDARD_EXPENSE_CATEGORIES:
        if item["name"].lower() in existing_names:
            continue
        row = ExpenseCategory(**item)
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def create_expense_category(db: Session, payload: ExpenseCategoryCreate) -> ExpenseCategory:
    existing = db.query(ExpenseCategory).filter(func.lower(ExpenseCategory.name) == payload.name.strip().lower()).first()
    if existing:
        return existing
    row = ExpenseCategory(name=payload.name.strip(), description=payload.description)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_expenses(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    category_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[Expense], int]:
    query = db.query(Expense)
    query = _apply_expense_filters(query, category_id=category_id, start_date=start_date, end_date=end_date)
    total = query.count()
    rows = query.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).offset(skip).limit(limit).all()
    return rows, total


def create_expense(db: Session, payload: ExpenseCreate, recorded_by: UUID | None) -> Expense:
    row = Expense(**payload.model_dump(), recorded_by=recorded_by)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def expense_totals(db: Session) -> dict:
    today = date.today()
    month_total = (
        db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
        .filter(
            extract("year", Expense.expense_date) == today.year,
            extract("month", Expense.expense_date) == today.month,
        )
        .scalar()
    )
    year_total = (
        db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
        .filter(extract("year", Expense.expense_date) == today.year)
        .scalar()
    )
    return {
        "expenses_this_month": float(month_total or 0),
        "expenses_this_year": float(year_total or 0),
    }


def monthly_expense_report(
    db: Session,
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: UUID | None = None,
) -> list[dict]:
    year = year or date.today().year
    query = db.query(
        extract("month", Expense.expense_date).label("month"),
        func.coalesce(func.sum(Expense.amount), 0).label("total_amount"),
    ).filter(extract("year", Expense.expense_date) == year)
    query = _apply_expense_filters(query, category_id=category_id, start_date=start_date, end_date=end_date)
    rows = (
        query
        .group_by(extract("month", Expense.expense_date))
        .order_by(extract("month", Expense.expense_date))
        .all()
    )
    return [{"month": int(row.month), "value": float(row.total_amount)} for row in rows]


def finance_summary(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    batch_id: UUID | None = None,
    fund_id: UUID | None = None,
    category_id: UUID | None = None,
) -> dict:
    donation_query = _apply_donation_filters(db.query(Donation), batch_id=batch_id, fund_id=fund_id, start_date=start_date, end_date=end_date)
    expense_query = _apply_expense_filters(db.query(Expense), category_id=category_id, start_date=start_date, end_date=end_date)

    income_total = donation_query.with_entities(func.coalesce(func.sum(Donation.amount), Decimal("0.00"))).scalar() or Decimal("0.00")
    expense_total = expense_query.with_entities(func.coalesce(func.sum(Expense.amount), Decimal("0.00"))).scalar() or Decimal("0.00")

    income_by_fund = (
        _apply_donation_filters(
            db.query(DonationFund.name, func.coalesce(func.sum(Donation.amount), Decimal("0.00")).label("total_amount"))
            .join(Donation, Donation.fund_id == DonationFund.id),
            batch_id=batch_id,
            fund_id=fund_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(DonationFund.name)
        .order_by(func.coalesce(func.sum(Donation.amount), Decimal("0.00")).desc(), DonationFund.name.asc())
        .all()
    )

    expenses_by_category = (
        _apply_expense_filters(
            db.query(ExpenseCategory.name, func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"))
            .join(Expense, Expense.category_id == ExpenseCategory.id),
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
        )
        .group_by(ExpenseCategory.name)
        .order_by(func.coalesce(func.sum(Expense.amount), Decimal("0.00")).desc(), ExpenseCategory.name.asc())
        .all()
    )

    return {
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "batch_id": str(batch_id) if batch_id else None,
            "fund_id": str(fund_id) if fund_id else None,
            "category_id": str(category_id) if category_id else None,
        },
        "income_total": float(income_total),
        "expense_total": float(expense_total),
        "net_total": float(income_total - expense_total),
        "income_by_fund": [{"name": row.name, "value": float(row.total_amount)} for row in income_by_fund],
        "expenses_by_category": [{"name": row.name, "value": float(row.total_amount)} for row in expenses_by_category],
    }


def member_giving_summary(db: Session, member_id: UUID) -> dict:
    totals = (
        db.query(
            func.coalesce(func.sum(Donation.amount), Decimal("0.00")).label("total_amount"),
            func.count(Donation.id).label("entry_count"),
        )
        .filter(Donation.member_id == member_id)
        .first()
    )
    tithe_total = (
        db.query(func.coalesce(func.sum(Donation.amount), Decimal("0.00")))
        .join(DonationFund, DonationFund.id == Donation.fund_id)
        .filter(Donation.member_id == member_id, func.lower(DonationFund.code) == "tithe")
        .scalar()
    )
    latest = (
        db.query(Donation)
        .filter(Donation.member_id == member_id)
        .order_by(Donation.donation_date.desc(), Donation.created_at.desc())
        .first()
    )
    by_fund = (
        db.query(
            DonationFund.name.label("fund_name"),
            func.coalesce(func.sum(Donation.amount), Decimal("0.00")).label("total_amount"),
        )
        .join(DonationFund, DonationFund.id == Donation.fund_id)
        .filter(Donation.member_id == member_id)
        .group_by(DonationFund.name)
        .order_by(func.coalesce(func.sum(Donation.amount), Decimal("0.00")).desc(), DonationFund.name.asc())
        .all()
    )
    return {
        "total_giving": float(totals.total_amount or 0),
        "giving_entries": int(totals.entry_count or 0),
        "tithe_total": float(tithe_total or 0),
        "last_giving_date": latest.donation_date if latest else None,
        "fund_breakdown": [{"fund": row.fund_name, "value": float(row.total_amount)} for row in by_fund],
        "recent_entries": member_history(db, member_id)[:10],
    }
