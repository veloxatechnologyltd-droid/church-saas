"""Central tenant scoping: the one place that keeps a request inside its church.

How it works
------------
After authentication, ``bind_tenant(db, church_id, branch_id, default_branch_id)`` stores
the active church (and branch, for branch-scoped users) in ``Session.info``. From then on,
for that session:

* **Reads** - every ORM ``SELECT`` (including ``db.query(func.sum(Donation.amount))``,
  joins, subqueries and relationship lazy-loads) gets ``church_id = :active`` added for
  every ``ChurchScoped`` entity via ``with_loader_criteria``. CRUD code cannot forget it.
* **Bulk UPDATE / DELETE** through the ORM are scoped the same way.
* **Writes** - ``before_flush`` stamps ``church_id`` on new tenant rows and refuses any
  new or modified row whose ``church_id`` belongs to another church.
* **Branches** - a branch-scoped user only sees rows of their branch for the models in
  ``BRANCH_FILTERED``; new rows are stamped with their branch (it overrides the request).
  Church-wide users' new rows default to the church's main branch.
* **Row-level security** - ``app.current_church`` is set on every transaction, and the
  Postgres RLS policies (migration 000015) use it as a backstop for raw SQL.

Sessions with no tenant bound (login, signup, platform-admin and background jobs) are not
filtered. Those code paths must filter by ``church_id`` explicitly.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import event, or_, text
from sqlalchemy.orm import Session, with_loader_criteria

from app.models.tenant import ChurchScoped

TENANT_KEY = "tenant_church_id"
BRANCH_KEY = "tenant_branch_id"
DEFAULT_BRANCH_KEY = "tenant_default_branch_id"


class TenantViolation(RuntimeError):
    """Application code tried to write a row that belongs to another church."""


def bind_tenant(db: Session, church_id: UUID | None, branch_id: UUID | None = None, default_branch_id: UUID | None = None) -> None:
    """Scope ``db`` to one church (``None`` clears the scope)."""
    if church_id is None:
        clear_tenant(db)
        return
    db.info[TENANT_KEY] = church_id
    db.info[BRANCH_KEY] = branch_id
    db.info[DEFAULT_BRANCH_KEY] = branch_id or default_branch_id
    # The current transaction may already be open (the auth lookup ran in it), so
    # set the RLS variable now as well as on every later transaction begin.
    _set_rls(db.connection(), church_id)


def clear_tenant(db: Session) -> None:
    for key in (TENANT_KEY, BRANCH_KEY, DEFAULT_BRANCH_KEY):
        db.info.pop(key, None)


def current_church_id(db: Session) -> UUID | None:
    return db.info.get(TENANT_KEY)


def current_branch_id(db: Session) -> UUID | None:
    return db.info.get(BRANCH_KEY)


def _set_rls(connection, church_id: UUID | None) -> None:
    connection.execute(
        text("SELECT set_config('app.current_church', :cid, true)"),
        {"cid": str(church_id) if church_id else ""},
    )


def _branch_models():
    """(model, branch column name, include church-wide NULL rows) for branch-scoped users."""
    from app.models import (
        Announcement, AttendanceSession, Donation, Event, Expense, FinanceBatch, Group, Member, PastoralLog, Visitor,
    )

    return (
        (Member, "home_branch_id", False),
        (AttendanceSession, "branch_id", False),
        (FinanceBatch, "branch_id", False),
        (Donation, "branch_id", False),
        (Expense, "branch_id", False),
        (Group, "branch_id", False),
        (PastoralLog, "branch_id", False),
        (Visitor, "branch_id", False),
        # Church-wide announcements and events are for everyone.
        (Announcement, "branch_id", True),
        (Event, "branch_id", True),
    )


@event.listens_for(Session, "after_begin")
def _after_begin(session, transaction, connection):  # pragma: no cover - exercised via the API
    church_id = session.info.get(TENANT_KEY)
    if church_id is not None:
        _set_rls(connection, church_id)


@event.listens_for(Session, "do_orm_execute")
def _scope_orm_statements(state):
    church_id = state.session.info.get(TENANT_KEY)
    if church_id is None:
        return
    if not (state.is_select or state.is_update or state.is_delete):
        return
    if state.execution_options.get("skip_tenant_scope"):
        return

    options = [
        with_loader_criteria(
            ChurchScoped,
            lambda cls: cls.church_id == church_id,
            include_aliases=True,
            track_closure_variables=False,
        )
    ]
    branch_id = state.session.info.get(BRANCH_KEY)
    if branch_id is not None:
        for model, column, include_null in _branch_models():
            col = getattr(model, column)
            criterion = or_(col == branch_id, col.is_(None)) if include_null else (col == branch_id)
            options.append(with_loader_criteria(model, criterion, include_aliases=True))
    state.statement = state.statement.options(*options)


@event.listens_for(Session, "before_flush")
def _stamp_and_guard(session, flush_context, instances):
    church_id = session.info.get(TENANT_KEY)
    if church_id is None:
        return
    branch_id = session.info.get(BRANCH_KEY)
    default_branch_id = session.info.get(DEFAULT_BRANCH_KEY)
    branch_columns = {model: (column, include_null) for model, column, include_null in _branch_models()}

    for obj in session.new:
        if not isinstance(obj, ChurchScoped):
            continue
        if obj.church_id is None:
            obj.church_id = church_id
        elif obj.church_id != church_id:
            raise TenantViolation(f"Refusing to create {type(obj).__name__} in another church")
        column, church_wide_allowed = branch_columns.get(type(obj), (None, False))
        if column:
            if branch_id is not None:
                setattr(obj, column, branch_id)  # branch users can only write to their branch
            elif getattr(obj, column) is None and default_branch_id is not None and not church_wide_allowed:
                setattr(obj, column, default_branch_id)

    for obj in list(session.dirty) + list(session.deleted):
        if isinstance(obj, ChurchScoped) and obj.church_id is not None and obj.church_id != church_id:
            raise TenantViolation(f"Refusing to modify {type(obj).__name__} of another church")
