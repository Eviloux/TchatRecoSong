from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubmissionRequestCreate(BaseModel):
    twitch_user: str
    comment: Optional[str] = None


class SubmissionRequestPublic(BaseModel):
    token: str
    twitch_user: str
    comment: Optional[str] = None
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class SubmissionFulfillPayload(BaseModel):
    link: str
