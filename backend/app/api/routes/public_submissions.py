"""Public endpoint allowing viewers to submit song links."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import song as crud_song
from app.database.connection import get_db
from app.schemas.public_submission import PublicSubmissionPayload
from app.schemas.song import SongOut
from app.services.song_metadata import MetadataError, fetch_song_metadata

router = APIRouter()

YOUTUBE_REGEX = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/", re.IGNORECASE)
SPOTIFY_REGEX = re.compile(r"^(https?://)?(open\.)?spotify\.com/", re.IGNORECASE)


def _validate_link(link: str) -> str:
    cleaned = link.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le lien est requis.")

    if not (YOUTUBE_REGEX.match(cleaned) or SPOTIFY_REGEX.match(cleaned)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les liens YouTube et Spotify sont autorisés.",
        )
    return cleaned


@router.post("/", response_model=SongOut, status_code=status.HTTP_201_CREATED)
def submit_song(
    payload: PublicSubmissionPayload, db: Session = Depends(get_db)
) -> SongOut:
    link = _validate_link(payload.link)

    try:
        metadata = fetch_song_metadata(link)
    except MetadataError as exc:  # pragma: no cover - dépend des APIs externes
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    song = crud_song.add_or_increment_song(db, metadata)
    if song is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chanson bannie")

    return song
