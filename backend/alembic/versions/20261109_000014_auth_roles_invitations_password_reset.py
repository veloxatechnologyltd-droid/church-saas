"""Auth: move roles to memberships, add platform admin flag, invitations, password reset.

* users: drop the deprecated ``role`` and ``member_id`` (they live on ``memberships``
  since Phase 1); add ``is_platform_admin`` and ``password_changed_at``.
* invitations: tenant table; only a hash of the emailed token is stored.
* password_reset_tokens: global; only a hash of the emailed token is stored.

Like migration 000012 this assumes an empty ``users`` table: a user's old ``role``
cannot become a membership without knowing which church they belong to, so a database
that already has users must be imported with a script instead (SAAS_CHECKLIST Phase 9).

Downgrade re-adds ``users.role`` and backfills it from the user's oldest membership
(church_admin -> superadmin); users with no membership get ``member``. ``member_id`` is
not restored (it lives per church on memberships).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261109_000014"
down_revision = "20261109_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT count(*) FROM users")).scalar():
        raise RuntimeError(
            "users already contains rows. Their roles cannot be converted to memberships "
            "automatically; import existing users with a dedicated script instead "
            "(SAAS_CHECKLIST Phase 9)."
        )

    op.drop_constraint("users_member_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "member_id")
    op.drop_column("users", "role")
    op.add_column("users", sa.Column("is_platform_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("church_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("churches.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
        sa.CheckConstraint(
            "role IN ('church_admin', 'secretary', 'finance', 'group_leader', 'member')",
            name="ck_invitations_role",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "church_id"], ["branches.id", "branches.church_id"],
            name="fk_invitations_branch_id_same_church",
        ),
        sa.ForeignKeyConstraint(
            ["member_id", "church_id"], ["members.id", "members.church_id"],
            name="fk_invitations_member_id_same_church",
        ),
    )
    op.create_index("ix_invitations_church_id", "invitations", ["church_id"])
    op.create_index(
        "uq_invitations_pending_email", "invitations", ["church_id", "email"],
        unique=True, postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_invitations_pending_email", table_name="invitations")
    op.drop_index("ix_invitations_church_id", table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.add_column("users", sa.Column("role", sa.String(), server_default="member", nullable=False))
    op.execute(
        """
        UPDATE users SET role = CASE m.role WHEN 'church_admin' THEN 'superadmin' ELSE m.role END
        FROM (SELECT DISTINCT ON (user_id) user_id, role FROM memberships ORDER BY user_id, created_at) m
        WHERE users.id = m.user_id
        """
    )
    op.alter_column("users", "role", server_default=None)
    op.add_column("users", sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("users_member_id_fkey", "users", "members", ["member_id"], ["id"])
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "is_platform_admin")
