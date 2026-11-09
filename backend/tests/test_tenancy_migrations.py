"""Migration-level guarantees: the chain builds from empty, matches the models, and reverses."""
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

import app.models  # noqa: F401  registers every model on Base.metadata; without it the metadata is empty
from app.db.database import Base
from tests.conftest import run_alembic

PRE_TENANCY_REVISION = "20260729_000010"
PRE_AUTH_REVISION = "20261109_000013"

TENANT_TABLES = [
    "families", "members", "attendance_sessions", "attendance_records",
    "finance_batches", "donation_funds", "donations", "expense_categories",
    "expenses", "groups", "group_members", "events", "event_registrations",
    "communications", "reminder_schedules", "reminder_runs", "announcements",
    "pastoral_logs", "audit_logs",
]
# Tables that legitimately have no church_id. Anything new must be added here on purpose.
GLOBAL_TABLES = {"users", "churches", "password_reset_tokens"}
# Tables that carry a nullable branch column, and its name.
BRANCH_COLUMNS = {
    "members": "home_branch_id", "attendance_sessions": "branch_id", "finance_batches": "branch_id",
    "donations": "branch_id", "expenses": "branch_id", "groups": "branch_id", "events": "branch_id",
    "announcements": "branch_id", "pastoral_logs": "branch_id", "memberships": "branch_id",
    "invitations": "branch_id",
}


def schema_drift(engine) -> list:
    """Differences between the live schema and the SQLAlchemy models (what `alembic check` reports)."""
    with engine.connect() as conn:
        return compare_metadata(MigrationContext.configure(conn), Base.metadata)


def test_models_match_migrated_schema(migrated_engine):
    assert schema_drift(migrated_engine) == []


def test_every_table_is_tenant_scoped_or_explicitly_global(migrated_engine):
    """Guard for the future: a new table without church_id fails here until someone decides."""
    insp = inspect(migrated_engine)
    scoped = set()
    for table in Base.metadata.tables:
        if table in GLOBAL_TABLES:
            continue
        cols = {c["name"]: c for c in insp.get_columns(table)}
        assert "church_id" in cols, f"{table} has no church_id (add it, or list it in GLOBAL_TABLES on purpose)"
        assert cols["church_id"]["nullable"] is False, f"{table}.church_id must be NOT NULL"
        fks = [fk for fk in insp.get_foreign_keys(table) if fk["constrained_columns"] == ["church_id"]]
        assert fks and fks[0]["referred_table"] == "churches", f"{table}.church_id must reference churches.id"
        scoped.add(table)
    assert set(TENANT_TABLES) | {"branches", "memberships", "invitations"} == scoped


def test_branch_columns_exist_and_are_nullable(migrated_engine):
    insp = inspect(migrated_engine)
    for table, column in BRANCH_COLUMNS.items():
        cols = {c["name"]: c for c in insp.get_columns(table)}
        assert column in cols and cols[column]["nullable"] is True, f"{table}.{column}"


def test_every_tenant_table_leads_an_index_with_church_id(migrated_engine):
    insp = inspect(migrated_engine)
    for table in TENANT_TABLES + ["branches", "memberships", "invitations"]:
        leading = [ix["column_names"][0] for ix in insp.get_indexes(table)]
        leading += [uq["column_names"][0] for uq in insp.get_unique_constraints(table)]
        assert "church_id" in leading, f"{table} has no index/unique starting with church_id"


def test_upgrade_from_empty_leaves_no_ownerless_seed_rows(migrated_engine):
    with migrated_engine.connect() as conn:
        for table in ("donation_funds", "expense_categories", "groups"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0, table


def test_downgrade_then_upgrade_round_trips(scratch_database):
    url = scratch_database("roundtrip")
    engine = create_engine(url)
    run_alembic(url, "upgrade", "head")
    assert "churches" in inspect(engine).get_table_names()

    run_alembic(url, "downgrade", PRE_TENANCY_REVISION)
    insp = inspect(engine)
    assert not {"churches", "branches", "memberships"} & set(insp.get_table_names())
    assert "church_id" not in {c["name"] for c in insp.get_columns("members")}
    # The old global constraints are back, and the old plain FKs too.
    assert "uq_groups_name" in {u["name"] for u in insp.get_unique_constraints("groups")}
    assert "donations_member_id_fkey" in {f["name"] for f in insp.get_foreign_keys("donations")}

    run_alembic(url, "upgrade", "head")
    assert schema_drift(engine) == []
    engine.dispose()


def _revision(engine) -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()


def test_upgrade_refuses_a_database_that_already_holds_data(scratch_database):
    url = scratch_database("hasdata")
    engine = create_engine(url)
    run_alembic(url, "upgrade", PRE_TENANCY_REVISION)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO members (id, first_name, last_name, membership_class_completed, is_family_head) "
            "VALUES (gen_random_uuid(), 'Ama', 'Mensah', false, false)"
        ))
    result = run_alembic(url, "upgrade", "head", check=False)
    assert result.returncode != 0
    assert "members already contains rows" in result.stderr
    assert _revision(engine) == PRE_TENANCY_REVISION  # transactional DDL: nothing half-applied
    engine.dispose()


def test_custom_row_in_a_seeded_table_fails_loudly_and_rolls_back(scratch_database):
    url = scratch_database("customrow")
    engine = create_engine(url)
    run_alembic(url, "upgrade", PRE_TENANCY_REVISION)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO groups (id, name) VALUES (gen_random_uuid(), 'Custom Ministry')"))
    result = run_alembic(url, "upgrade", "head", check=False)
    assert result.returncode != 0
    assert 'column "church_id"' in result.stderr and "contains null values" in result.stderr
    assert _revision(engine) == PRE_TENANCY_REVISION
    with engine.connect() as conn:  # the seed deletion rolled back with the failed migration
        assert conn.execute(text("SELECT count(*) FROM groups")).scalar() == 11
    engine.dispose()


# ------------------------------------------------------- migration 000014 (auth)

def test_users_no_longer_hold_a_role_or_member_link(migrated_engine):
    columns = {c["name"]: c for c in inspect(migrated_engine).get_columns("users")}
    assert "role" not in columns and "member_id" not in columns
    assert columns["is_platform_admin"]["nullable"] is False
    assert columns["password_changed_at"]["nullable"] is True


def test_new_users_are_not_platform_admins_by_default(session):
    from tests.helpers import make_user
    user = make_user(session)
    session.refresh(user)
    assert user.is_platform_admin is False and user.password_changed_at is None


def test_auth_migration_refuses_a_database_that_already_has_users(scratch_database):
    url = scratch_database("hasusers")
    engine = create_engine(url)
    run_alembic(url, "upgrade", PRE_AUTH_REVISION)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO users (id, email, hashed_password, role, is_active) "
            "VALUES (gen_random_uuid(), 'old@example.com', 'x', 'superadmin', true)"
        ))
    result = run_alembic(url, "upgrade", "head", check=False)
    assert result.returncode != 0 and "users already contains rows" in result.stderr
    assert _revision(engine) == PRE_AUTH_REVISION
    assert "role" in {c["name"] for c in inspect(engine).get_columns("users")}  # nothing dropped
    engine.dispose()


def test_auth_downgrade_restores_roles_from_memberships(scratch_database):
    url = scratch_database("authdown")
    engine = create_engine(url)
    run_alembic(url, "upgrade", "head")
    with engine.begin() as conn:
        church_id = conn.execute(text("INSERT INTO churches (id, name, slug) VALUES (gen_random_uuid(), 'A', 'a-church') RETURNING id")).scalar()
        for email in ("admin@example.com", "fin@example.com", "nobody@example.com"):
            conn.execute(text("INSERT INTO users (id, email, hashed_password) VALUES (gen_random_uuid(), :e, 'x')"), {"e": email})
        for email, role in (("admin@example.com", "church_admin"), ("fin@example.com", "finance")):
            conn.execute(
                text("INSERT INTO memberships (id, church_id, user_id, role) SELECT gen_random_uuid(), :c, id, :r FROM users WHERE email = :e"),
                {"c": church_id, "r": role, "e": email},
            )
    run_alembic(url, "downgrade", PRE_AUTH_REVISION)
    with engine.connect() as conn:
        roles = dict(conn.execute(text("SELECT email, role FROM users")).all())
    assert roles == {"admin@example.com": "superadmin", "fin@example.com": "finance", "nobody@example.com": "member"}
    engine.dispose()
