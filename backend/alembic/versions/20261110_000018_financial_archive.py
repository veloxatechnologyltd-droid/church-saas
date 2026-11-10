"""Anonymised archive of paid invoices, kept after a closed church's data is purged.

Tax and accounting rules require keeping records of money received, but not the church's
members or any personal data. One row per paid invoice, with its payments as JSON. It has no
foreign key to ``churches`` (the church is gone) and no RLS (platform data, not tenant data).
Rows are deleted by the purge job after ``FINANCIAL_RETENTION_YEARS``.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20261110_000018'
down_revision = '20261110_000017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_archive",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("closed_church_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("church_name", sa.String(), nullable=False),
        sa.Column("church_slug", sa.String(), nullable=False),
        sa.Column("invoice_number", sa.String(), nullable=False, unique=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("plan_code", sa.String(), nullable=True),
        sa.Column("sms_credits", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("provider_ref", sa.String(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invoice_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payments", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_financial_archive_archived_at", "financial_archive", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_financial_archive_archived_at", table_name="financial_archive")
    op.drop_table("financial_archive")
