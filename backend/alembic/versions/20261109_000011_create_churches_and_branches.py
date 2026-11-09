"""Create the tenancy root tables: churches and branches."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261109_000011"
down_revision = "20260729_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "churches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("primary_color", sa.String(), nullable=True),
        sa.Column("secondary_color", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), server_default="Africa/Accra", nullable=False),
        sa.Column("currency", sa.String(), server_default="GHS", nullable=False),
        sa.Column("status", sa.String(), server_default="trialing", nullable=False),
        sa.Column("plan", sa.String(), server_default="trial", nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sms_sender_id", sa.String(), nullable=True),
        sa.Column("email_from", sa.String(), nullable=True),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_churches_slug"),
        sa.CheckConstraint(r"slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="ck_churches_slug_format"),
        sa.CheckConstraint(
            "status IN ('trialing', 'active', 'suspended', 'closed')", name="ck_churches_status"
        ),
    )

    op.create_table(
        "branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("church_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("churches.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_main", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Target for same-church composite FKs from tenant tables.
        sa.UniqueConstraint("id", "church_id", name="uq_branches_id_church_id"),
        sa.UniqueConstraint("church_id", "name", name="uq_branches_church_name"),
    )
    # At most one main branch per church.
    op.create_index(
        "uq_branches_one_main_per_church",
        "branches",
        ["church_id"],
        unique=True,
        postgresql_where=sa.text("is_main"),
    )


def downgrade() -> None:
    op.drop_index("uq_branches_one_main_per_church", table_name="branches")
    op.drop_table("branches")
    op.drop_table("churches")
