import uuid

from sqlalchemy import Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tenant import ChurchScoped, id_church_unique


class Family(ChurchScoped, Base):
    __tablename__ = "families"
    __table_args__ = (
        id_church_unique("families"),
        Index("ix_families_church_id", "church_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    members = relationship("Member", back_populates="family", foreign_keys="Member.family_id")
