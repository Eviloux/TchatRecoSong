from __future__ import annotations

from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.submission_request import SubmissionRequest


def create_request(
    db: Session,
    *,
    twitch_user: str,
    comment: Optional[str],
    ttl_minutes: int,
) -> SubmissionRequest:
    token = token_urlsafe(12)
    expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    request = SubmissionRequest(
        token=token,
        twitch_user=twitch_user,
        comment=comment,
        expires_at=expires_at,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_active_requests(db: Session) -> Iterable[SubmissionRequest]:
    now = datetime.utcnow()
    return (
        db.query(SubmissionRequest)
        .filter(SubmissionRequest.consumed_at.is_(None))
        .filter(SubmissionRequest.expires_at > now)
        .order_by(SubmissionRequest.created_at.asc())
        .all()
    )


def get_request_by_token(db: Session, token: str) -> Optional[SubmissionRequest]:
    now = datetime.utcnow()
    request = (
        db.query(SubmissionRequest)
        .filter(SubmissionRequest.token == token)
        .filter(SubmissionRequest.expires_at > now)
        .first()
    )
    return request


def mark_consumed(db: Session, request: SubmissionRequest) -> SubmissionRequest:
    request.consumed_at = datetime.utcnow()
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def expire_old_requests(db: Session) -> int:
    """Cleanup helper to delete entries that are no longer needed."""

    now = datetime.utcnow()
    deleted = (
        db.query(SubmissionRequest)
        .filter(SubmissionRequest.expires_at <= now)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted
