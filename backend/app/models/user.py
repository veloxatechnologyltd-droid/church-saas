import uuid

from sqlalchemy import Boolean, Column, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class User(Base):
    """Global login identity. A user's role in a church lives on ``memberships``.

    ``is_platform_admin`` marks the product owner's operator accounts. It is a flag,
    not a church role: a platform admin has no powers inside a church unless they
    also hold a membership there (or impersonate, which is audited, Phase 5).
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_platform_admin = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Tokens issued before this instant are rejected (set on password change/reset).
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
