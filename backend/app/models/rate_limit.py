"""Shared rate-limit counters (platform infrastructure: no church_id, no RLS)."""
from sqlalchemy import BigInteger, Column, Index, Integer, String

from app.db.database import Base


class RateLimitHit(Base):
    __tablename__ = "rate_limit_hits"

    key = Column(String(300), primary_key=True)
    window_start = Column(BigInteger, primary_key=True)
    expires_at = Column(BigInteger, nullable=False)
    hits = Column(Integer, nullable=False, server_default="0")

    __table_args__ = (Index("ix_rate_limit_hits_expires_at", "expires_at"),)
