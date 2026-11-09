import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, UniqueConstraint, String, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, same_church_fk

# Roles a user can hold *inside one church*. ``platform_admin`` is deliberately not
# here: it is a platform-level capability, never a church membership (see Phase 2).
CHURCH_ROLES = ("church_admin", "secretary", "finance", "group_leader", "member")


class Membership(ChurchScoped, Base):
    """Links a global user to one church with a role.

    ``branch_id`` NULL means church-wide; set means limited to that branch.
    ``member_id`` links the login to that church's member profile (a profile is
    per church, so a user in two churches has two profiles).
    """

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "church_id", name="uq_memberships_user_church"),
        CheckConstraint(
            "role IN ('church_admin', 'secretary', 'finance', 'group_leader', 'member')",
            name="ck_memberships_role",
        ),
        same_church_fk("memberships", "branch_id", "branches"),
        same_church_fk("memberships", "member_id", "members"),
        Index("ix_memberships_church_id", "church_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    member_id = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")
    church = relationship("Church")
    branch = relationship("Branch", foreign_keys=[branch_id])
    member = relationship("Member", foreign_keys=[member_id])
