"""Schemas used by the public submission endpoint."""

from pydantic import BaseModel, Field


class PublicSubmissionPayload(BaseModel):
    link: str = Field(max_length=2000)
    comment: str | None = Field(default=None, max_length=1000)
