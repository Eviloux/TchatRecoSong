"""Public endpoint allowing viewers to submit song links."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.crud import song as crud_song
from app.database.connection import get_db
from app.schemas.public_submission import PublicSubmissionPayload
from app.schemas.song import SongOut
from app.services.song_metadata import MetadataError, fetch_song_metadata
from app.utils.links import InvalidLinkError, normalize_song_link
from app.utils.rate_limit import limiter

router = APIRouter()


@router.post("/", response_model=SongOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def submit_song(
    request: Request, payload: PublicSubmissionPayload, db: Session = Depends(get_db)
) -> SongOut:
    try:
        link, _ = normalize_song_link(payload.link)
    except InvalidLinkError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        metadata = fetch_song_metadata(link)
    except MetadataError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    comment = (payload.comment or "").strip()
    if comment:
        metadata.comment = comment

    song = crud_song.add_or_increment_song(db, metadata)
    if song is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chanson bannie")

    return song
