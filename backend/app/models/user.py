import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # DEPRECATED (Phase 1): a user's role now lives on ``memberships`` (per church).
    # Auth still reads these two columns until Phase 2 moves it to memberships;
    # both are dropped in the Phase 2 migration.
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    member_id = Column(UUID(as_uuid=True), ForeignKey("members.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
