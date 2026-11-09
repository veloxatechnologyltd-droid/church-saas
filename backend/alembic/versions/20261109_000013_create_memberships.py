"""Create memberships: a global user's role in one church (church-wide or one branch)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261109_000013"
down_revision = "20261109_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("church_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("churches.id"), nullable=False),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "church_id", name="uq_memberships_user_church"),
        sa.CheckConstraint(
            "role IN ('church_admin', 'secretary', 'finance', 'group_leader', 'member')",
            name="ck_memberships_role",
        ),
        # The branch and the member profile must belong to the same church.
        sa.ForeignKeyConstraint(
            ["branch_id", "church_id"], ["branches.id", "branches.church_id"],
            name="fk_memberships_branch_id_same_church",
        ),
        sa.ForeignKeyConstraint(
            ["member_id", "church_id"], ["members.id", "members.church_id"],
            name="fk_memberships_member_id_same_church",
        ),
    )
    op.create_index("ix_memberships_church_id", "memberships", ["church_id"])


def downgrade() -> None:
    op.drop_index("ix_memberships_church_id", table_name="memberships")
    op.drop_table("memberships")
