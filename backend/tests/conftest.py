"""Shared pytest fixtures: a real Postgres test database built by running Alembic.

Safety: tests must NEVER touch the dev database (or anything else). The test URL is
derived from the configured one with the database name replaced by ``*_test``, and
every create/drop below asserts that suffix and a local host first.

``DATABASE_URL`` is overridden here, before any ``app`` import, so ``app.db.database``
and ``alembic/env.py`` (which both read ``settings.DATABASE_URL``) point at the test DB.
"""
import os
import subprocess
import sys
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_NAME = "church_saas_test"

# Resolve the base (dev) URL the same way the app would, then derive the test URL.
os.chdir(BACKEND_DIR)  # so pydantic-settings finds backend/.env
sys.path.insert(0, str(BACKEND_DIR))
from app.core.config import Settings  # noqa: E402

_base_url = make_url(Settings().DATABASE_URL)
TEST_URL = _base_url.set(database=TEST_DB_NAME).render_as_string(hide_password=False)
os.environ["DATABASE_URL"] = TEST_URL


def _assert_safe(db_name: str, host: str | None) -> None:
    assert db_name.endswith("_test"), f"refusing to touch non-test database {db_name!r}"
    assert host in (None, "localhost", "127.0.0.1"), f"refusing non-local test database host {host!r}"


def recreate_database(db_name: str) -> str:
    """Drop and create an empty database next to the dev one; returns its URL."""
    url = make_url(TEST_URL).set(database=db_name)
    _assert_safe(url.database, url.host)
    admin = psycopg2.connect(
        dbname="postgres", user=url.username, password=url.password, host=url.host, port=url.port
    )
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
            (db_name,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cur.execute(f'CREATE DATABASE "{db_name}"')
    admin.close()
    return url.render_as_string(hide_password=False)


def run_alembic(url: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run the alembic CLI against ``url`` (same entrypoint Render's preDeployCommand uses)."""
    _assert_safe(make_url(url).database, make_url(url).host)
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"alembic {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


@pytest.fixture(scope="session")
def migrated_engine():
    """Empty database -> ``alembic upgrade head``. Built once per test session."""
    url = recreate_database(TEST_DB_NAME)
    run_alembic(url, "upgrade", "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture()
def session(migrated_engine):
    """A Session inside a transaction that is rolled back after each test.

    ``create_savepoint`` lets a test trigger an IntegrityError inside
    ``session.begin_nested()`` without poisoning the rest of the test.
    """
    connection = migrated_engine.connect()
    outer = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield db
    finally:
        db.close()
        outer.rollback()
        connection.close()


@pytest.fixture()
def scratch_database():
    """Factory for a throwaway empty database (for migration up/down tests)."""
    created: list[str] = []

    def make(suffix: str) -> str:
        name = f"church_saas_{suffix}_test"  # must still end in _test (see _assert_safe)
        created.append(name)
        return recreate_database(name)

    yield make
    for name in created:
        url = make_url(TEST_URL).set(database=name)
        _assert_safe(url.database, url.host)
        admin = psycopg2.connect(
            dbname="postgres", user=url.username, password=url.password, host=url.host, port=url.port
        )
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
        admin.close()
