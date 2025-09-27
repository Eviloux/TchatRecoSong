from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from app.database.connection import Base


class SubmissionRequest(Base):
    """Represents a ``!reco`` command waiting for a viewer submission."""

    __tablename__ = "submission_requests"
    __table_args__ = (UniqueConstraint("token", name="uq_submission_token"),)

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(32), nullable=False, index=True)
    twitch_user = Column(String(255), nullable=False)
    comment = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
