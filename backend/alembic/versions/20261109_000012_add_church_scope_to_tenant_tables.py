"""Add church_id (tenant) and branch_id to tenant tables; enforce same-church references.

For each of the 19 tenant-owned tables this migration:
  * adds ``church_id UUID NOT NULL`` -> ``churches.id`` (no ON DELETE: deleting a
    church that still has data must fail),
  * adds a nullable ``branch_id`` (``members.home_branch_id``) where data is per-branch,
  * adds ``UNIQUE (id, church_id)`` on every table another tenant table references,
  * replaces each plain tenant->tenant FK with a composite ``(col, church_id)`` FK so
    the database rejects a reference to another church's row,
  * turns the global unique constraints into per-church ones,
  * adds composite ``(church_id, ...)`` indexes for the hot queries.

NOT NULL columns are added without a backfill: this repo starts from an empty
database. Running this against a database that already holds rows is meant to fail
loudly (use a data-import script instead, see SAAS_CHECKLIST Phase 9).

Global seed rows: migrations 000002/000005/000006 inserted 8 donation funds,
6 expense categories and the 10 Living Spring departments with no owner church.
Those belong to no tenant, so they are removed here (exact-name match, and only
when every other tenant table is empty). New churches get funds and expense
categories from the existing ``bootstrap`` endpoints at onboarding (Phase 5); the
departments are Living Spring specific and come back only via the Phase 9 import.
The downgrade does not re-insert them.

FKs to ``users`` stay plain: users are global, so "this user belongs to this
church" is checked via ``memberships`` in application code.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261109_000012"
down_revision = "20261109_000011"
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "families", "members", "attendance_sessions", "attendance_records",
    "finance_batches", "donation_funds", "donations", "expense_categories",
    "expenses", "groups", "group_members", "events", "event_registrations",
    "communications", "reminder_schedules", "reminder_runs", "announcements",
    "pastoral_logs", "audit_logs",
]

# table -> nullable branch column added to it
BRANCH_COLUMNS = {
    "members": "home_branch_id",
    "attendance_sessions": "branch_id",
    "finance_batches": "branch_id",
    "donations": "branch_id",
    "expenses": "branch_id",
    "groups": "branch_id",
    "events": "branch_id",
    "announcements": "branch_id",
    "pastoral_logs": "branch_id",
}

# tables that other tenant tables point at (``branches`` got its own in 000011)
ID_CHURCH_PARENTS = [
    "families", "members", "attendance_sessions", "finance_batches", "donation_funds",
    "expense_categories", "groups", "events", "communications", "reminder_schedules",
]

# (table, column, target, ondelete, replaces_existing_plain_fk)
SAME_CHURCH_FKS = [
    ("members", "family_id", "families", None, True),
    ("members", "home_branch_id", "branches", None, False),
    ("attendance_sessions", "branch_id", "branches", None, False),
    ("attendance_records", "session_id", "attendance_sessions", None, True),
    ("attendance_records", "member_id", "members", None, True),
    ("finance_batches", "branch_id", "branches", None, False),
    ("donations", "member_id", "members", None, True),
    ("donations", "batch_id", "finance_batches", None, True),
    ("donations", "fund_id", "donation_funds", None, True),
    ("donations", "branch_id", "branches", None, False),
    ("expenses", "category_id", "expense_categories", None, True),
    ("expenses", "branch_id", "branches", None, False),
    ("groups", "leader_id", "members", None, True),
    ("groups", "branch_id", "branches", None, False),
    ("group_members", "group_id", "groups", "CASCADE", True),
    ("group_members", "member_id", "members", "CASCADE", True),
    ("events", "branch_id", "branches", None, False),
    ("event_registrations", "event_id", "events", "CASCADE", True),
    ("event_registrations", "member_id", "members", "CASCADE", True),
    ("communications", "group_id", "groups", None, True),
    ("reminder_schedules", "group_id", "groups", None, True),
    ("reminder_runs", "schedule_id", "reminder_schedules", "CASCADE", True),
    ("reminder_runs", "communication_id", "communications", None, True),
    ("announcements", "branch_id", "branches", None, False),
    ("pastoral_logs", "member_id", "members", "CASCADE", True),
    ("pastoral_logs", "branch_id", "branches", None, False),
]

# (table, old global constraint, new per-church name, columns)
UNIQUE_SWAPS = [
    ("groups", "uq_groups_name", "uq_groups_church_name", ["name"]),
    ("donation_funds", "uq_donation_funds_name", "uq_donation_funds_church_name", ["name"]),
    ("donation_funds", "uq_donation_funds_code", "uq_donation_funds_church_code", ["code"]),
    ("expense_categories", "uq_expense_categories_name", "uq_expense_categories_church_name", ["name"]),
]

# (index name, table, columns). Tables whose per-church unique already leads with
# church_id (groups, donation_funds, expense_categories) need no extra index.
INDEXES = [
    ("ix_families_church_id", "families", ["church_id"]),
    ("ix_members_church_status", "members", ["church_id", "membership_status"]),
    ("ix_members_church_name", "members", ["church_id", "last_name", "first_name"]),
    ("ix_attendance_sessions_church_date", "attendance_sessions", ["church_id", "session_date"]),
    ("ix_attendance_records_church_session", "attendance_records", ["church_id", "session_id"]),
    ("ix_attendance_records_church_member", "attendance_records", ["church_id", "member_id"]),
    ("ix_finance_batches_church_date", "finance_batches", ["church_id", "service_date"]),
    ("ix_donations_church_date", "donations", ["church_id", "donation_date"]),
    ("ix_donations_church_member", "donations", ["church_id", "member_id"]),
    ("ix_expenses_church_date", "expenses", ["church_id", "expense_date"]),
    ("ix_group_members_church_id", "group_members", ["church_id"]),
    ("ix_events_church_start", "events", ["church_id", "start_datetime"]),
    ("ix_event_registrations_church_id", "event_registrations", ["church_id"]),
    ("ix_communications_church_sent", "communications", ["church_id", "sent_at"]),
    ("ix_reminder_schedules_church_active", "reminder_schedules", ["church_id", "is_active"]),
    ("ix_reminder_runs_church_id", "reminder_runs", ["church_id"]),
    ("ix_announcements_church_active_publish", "announcements", ["church_id", "is_active", "publish_at"]),
    ("ix_pastoral_logs_church_status_due", "pastoral_logs", ["church_id", "status", "follow_up_date"]),
    ("ix_pastoral_logs_church_member", "pastoral_logs", ["church_id", "member_id"]),
    ("ix_audit_logs_church_created", "audit_logs", ["church_id", "created_at"]),
]


# Names inserted by earlier migrations (see docstring). Matched exactly.
SEED_ROWS = {
    "donation_funds": [
        "Tithe", "Offering", "Harvest", "Thanksgiving", "Missions", "Welfare", "Building Fund", "Seed",
    ],
    "expense_categories": ["Utilities", "Welfare", "Missions", "Maintenance", "Programs", "Payroll"],
    "groups": [
        "Ushering", "Springs Harmony Choir", "Protocol Ministry", "Media, ICT & Publicity Ministry",
        "King's Kids Ministry", "GenNext", "Battle Axe", "Crowns of Glory", "Men of Honour",
        "Car Park Ministry",
    ],
}


def _remove_global_seed_rows() -> None:
    """Drop the ownerless seed rows, refusing to touch a database that holds real data."""
    bind = op.get_bind()
    for table in TENANT_TABLES:
        if table in SEED_ROWS:
            continue
        if bind.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar():
            raise RuntimeError(
                f"{table} already contains rows. This migration assumes an empty database; "
                "import existing data with a dedicated script instead (SAAS_CHECKLIST Phase 9)."
            )
    for table, names in SEED_ROWS.items():
        bind.execute(sa.text(f"DELETE FROM {table} WHERE name = ANY(:names)"), {"names": names})


def _fk_name(table: str, column: str) -> str:
    return f"fk_{table}_{column}_same_church"


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)

    _remove_global_seed_rows()

    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("church_id", uuid, nullable=False))
        op.create_foreign_key(f"fk_{table}_church_id_churches", table, "churches", ["church_id"], ["id"])

    for table, column in BRANCH_COLUMNS.items():
        op.add_column(table, sa.Column(column, uuid, nullable=True))

    for table in ID_CHURCH_PARENTS:
        op.create_unique_constraint(f"uq_{table}_id_church_id", table, ["id", "church_id"])

    for table, column, target, ondelete, replaces in SAME_CHURCH_FKS:
        if replaces:
            op.drop_constraint(f"{table}_{column}_fkey", table, type_="foreignkey")
        op.create_foreign_key(
            _fk_name(table, column), table, target,
            [column, "church_id"], ["id", "church_id"], ondelete=ondelete,
        )

    for table, old, new, columns in UNIQUE_SWAPS:
        op.drop_constraint(old, table, type_="unique")
        op.create_unique_constraint(new, table, ["church_id", *columns])

    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)

    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)

    for table, old, new, columns in reversed(UNIQUE_SWAPS):
        op.drop_constraint(new, table, type_="unique")
        op.create_unique_constraint(old, table, columns)

    for table, column, target, ondelete, replaces in reversed(SAME_CHURCH_FKS):
        op.drop_constraint(_fk_name(table, column), table, type_="foreignkey")
        if replaces:
            op.create_foreign_key(
                f"{table}_{column}_fkey", table, target, [column], ["id"], ondelete=ondelete,
            )

    for table in reversed(ID_CHURCH_PARENTS):
        op.drop_constraint(f"uq_{table}_id_church_id", table, type_="unique")

    for table, column in BRANCH_COLUMNS.items():
        op.drop_column(table, column)

    for table in reversed(TENANT_TABLES):
        op.drop_constraint(f"fk_{table}_church_id_churches", table, type_="foreignkey")
        op.drop_column(table, "church_id")
