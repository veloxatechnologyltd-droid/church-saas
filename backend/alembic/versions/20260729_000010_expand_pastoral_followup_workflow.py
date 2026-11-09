"""Expand pastoral follow-up into an assigned care workflow."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260729_000010"
down_revision = "20260729_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pastoral_logs",
        sa.Column("priority", sa.String(), server_default="normal", nullable=False),
    )
    op.add_column(
        "pastoral_logs",
        sa.Column("source", sa.String(), server_default="manual", nullable=False),
    )
    op.add_column(
        "pastoral_logs",
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "pastoral_logs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pastoral_logs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE pastoral_logs SET assigned_to = logged_by "
        "WHERE assigned_to IS NULL AND logged_by IS NOT NULL"
    )
    op.create_index("ix_pastoral_logs_status", "pastoral_logs", ["status"])
    op.create_index("ix_pastoral_logs_follow_up_date", "pastoral_logs", ["follow_up_date"])
    op.create_index("ix_pastoral_logs_assigned_to", "pastoral_logs", ["assigned_to"])


def downgrade() -> None:
    op.drop_index("ix_pastoral_logs_assigned_to", table_name="pastoral_logs")
    op.drop_index("ix_pastoral_logs_follow_up_date", table_name="pastoral_logs")
    op.drop_index("ix_pastoral_logs_status", table_name="pastoral_logs")
    op.drop_column("pastoral_logs", "updated_at")
    op.drop_column("pastoral_logs", "completed_at")
    op.drop_column("pastoral_logs", "assigned_to")
    op.drop_column("pastoral_logs", "source")
    op.drop_column("pastoral_logs", "priority")
