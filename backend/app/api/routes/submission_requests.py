from __future__ import annotations

import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import submission_request as crud_requests
from app.crud import song as crud_song
from app.database.connection import get_db
from app.schemas.song import SongOut
from app.schemas.submission_request import (
    SubmissionFulfillPayload,
    SubmissionRequestCreate,
    SubmissionRequestPublic,
)
from app.services.song_metadata import MetadataError, fetch_song_metadata
from app.services.auth import require_admin
from app.config import SUBMISSION_TTL_MINUTES

router = APIRouter()

YOUTUBE_REGEX = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/", re.IGNORECASE)
SPOTIFY_REGEX = re.compile(r"^(https?://)?(open\.)?spotify\.com/", re.IGNORECASE)


def _validate_link(link: str) -> None:
    if not (YOUTUBE_REGEX.match(link) or SPOTIFY_REGEX.match(link)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les liens YouTube et Spotify sont autorisés.",
        )


@router.post("/", response_model=SubmissionRequestPublic, dependencies=[Depends(require_admin)])
def create_submission_request(
    payload: SubmissionRequestCreate, db: Session = Depends(get_db)
) -> SubmissionRequestPublic:
    crud_requests.expire_old_requests(db)
    request = crud_requests.create_request(
        db,
        twitch_user=payload.twitch_user,
        comment=payload.comment,
        ttl_minutes=SUBMISSION_TTL_MINUTES,
    )
    return request


@router.get("/active", response_model=list[SubmissionRequestPublic])
def list_active_requests(db: Session = Depends(get_db)) -> list[SubmissionRequestPublic]:
    crud_requests.expire_old_requests(db)
    return list(crud_requests.get_active_requests(db))


@router.get("/{token}", response_model=SubmissionRequestPublic)
def get_request(token: str, db: Session = Depends(get_db)) -> SubmissionRequestPublic:
    crud_requests.expire_old_requests(db)
    request = crud_requests.get_request_by_token(db, token)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable ou expirée")
    return request


@router.post("/{token}/submit", response_model=SongOut)
def fulfill_request(
    token: str,
    payload: SubmissionFulfillPayload,
    db: Session = Depends(get_db),
) -> SongOut:
    crud_requests.expire_old_requests(db)
    request = crud_requests.get_request_by_token(db, token)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable ou expirée")

    _validate_link(payload.link)
    try:
        metadata = fetch_song_metadata(payload.link)
    except MetadataError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    song = crud_song.add_or_increment_song(db, metadata)
    if song is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chanson bannie")

    crud_requests.mark_consumed(db, request)
    return song
