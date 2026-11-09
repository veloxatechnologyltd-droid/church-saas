import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.models.tenant import ChurchScoped, same_church_fk


class Invitation(ChurchScoped, Base):
    """An invitation for an email address to join one church with a role.

    Only a SHA-256 hash of the emailed token is stored, so a database leak does not
    leak usable invite links. An invitation is single-use (``accepted_at``) and
    expires (``expires_at``); ``revoked_at`` cancels it.
    """

    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint(
            "role IN ('church_admin', 'secretary', 'finance', 'group_leader', 'member')",
            name="ck_invitations_role",
        ),
        same_church_fk("invitations", "branch_id", "branches"),
        same_church_fk("invitations", "member_id", "members"),
        # One pending invitation per email per church; re-inviting revokes the old one first.
        Index(
            "uq_invitations_pending_email",
            "church_id",
            "email",
            unique=True,
            postgresql_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
        ),
        Index("ix_invitations_church_id", "church_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)  # stored lower-cased
    role = Column(String, nullable=False)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    member_id = Column(UUID(as_uuid=True), nullable=True)
    token_hash = Column(String, nullable=False, unique=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
