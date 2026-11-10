"""Shared rate-limit counters.

Fixed-window counters keyed by ``(key, window_start)``, shared by every API instance
(serverless functions each have their own memory, so an in-process limiter cannot work).
Platform infrastructure, not tenant data: no ``church_id`` and no RLS policy.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20261110_000016'
down_revision = '20261109_000015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_hits",
        sa.Column("key", sa.String(length=300), nullable=False),
        sa.Column("window_start", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("key", "window_start"),
    )
    op.create_index("ix_rate_limit_hits_expires_at", "rate_limit_hits", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_rate_limit_hits_expires_at", table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")
