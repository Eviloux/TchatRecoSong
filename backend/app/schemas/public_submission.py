"""Schemas used by the public submission endpoint."""

from pydantic import BaseModel


class PublicSubmissionPayload(BaseModel):
    link: str
    comment: str | None = None
