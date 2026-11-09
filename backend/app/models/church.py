import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique

CHURCH_STATUSES = ("trialing", "active", "suspended", "closed")


class Church(Base):
    """A tenant. All church data hangs off this row via ``church_id``."""

    __tablename__ = "churches"
    __table_args__ = (
        # URL-safe slug: lowercase letters/digits separated by single hyphens.
        CheckConstraint(r"slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="ck_churches_slug_format"),
        CheckConstraint(
            "status IN ('trialing', 'active', 'suspended', 'closed')", name="ck_churches_status"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, nullable=True)
    secondary_color = Column(String, nullable=True)
    timezone = Column(String, nullable=False, default="Africa/Accra", server_default="Africa/Accra")
    currency = Column(String, nullable=False, default="GHS", server_default="GHS")
    status = Column(String, nullable=False, default="trialing", server_default="trialing")
    # Plain text until the plans table exists (Phase 7).
    plan = Column(String, nullable=False, default="trial", server_default="trial")
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    sms_sender_id = Column(String, nullable=True)
    email_from = Column(String, nullable=True)
    settings = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    branches = relationship("Branch", back_populates="church")


class Branch(ChurchScoped, Base):
    """A physical congregation/location inside a church. Each church has one main branch."""

    __tablename__ = "branches"
    __table_args__ = (
        id_church_unique("branches"),
        UniqueConstraint("church_id", "name", name="uq_branches_church_name"),
        # At most one main branch per church.
        Index(
            "uq_branches_one_main_per_church",
            "church_id",
            unique=True,
            postgresql_where=text("is_main"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    address = Column(Text, nullable=True)
    is_main = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    church = relationship("Church", back_populates="branches")
