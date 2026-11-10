"""Account closure: when a church was closed and when its data is permanently purged."""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20261110_000017'
down_revision = '20261110_000016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("churches", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("churches", sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_churches_purge_after", "churches", ["purge_after"],
        postgresql_where=sa.text("status = 'closed'"),
    )


def downgrade() -> None:
    op.drop_index("ix_churches_purge_after", table_name="churches")
    op.drop_column("churches", "purge_after")
    op.drop_column("churches", "closed_at")
