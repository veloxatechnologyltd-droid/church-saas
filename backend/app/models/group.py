import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique, same_church_fk


class Group(ChurchScoped, Base):
    """A church ministry or department. Groups intentionally have no sub-units."""

    __tablename__ = "groups"
    __table_args__ = (
        id_church_unique("groups"),
        UniqueConstraint("church_id", "name", name="uq_groups_church_name"),
        same_church_fk("groups", "leader_id", "members"),
        same_church_fk("groups", "branch_id", "branches"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    leader_id = Column(UUID(as_uuid=True), nullable=True)
    branch_id = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    leader = relationship("Member", foreign_keys=[leader_id])
    members = relationship("Member", secondary="group_members", viewonly=True)
    memberships = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        foreign_keys="GroupMember.group_id",
    )


class GroupMember(ChurchScoped, Base):
    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "member_id", name="uq_group_member"),
        same_church_fk("group_members", "group_id", "groups", ondelete="CASCADE"),
        same_church_fk("group_members", "member_id", "members", ondelete="CASCADE"),
        Index("ix_group_members_church_id", "church_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    group = relationship("Group", back_populates="memberships", foreign_keys=[group_id])
    member = relationship("Member", back_populates="group_memberships", foreign_keys=[member_id])
