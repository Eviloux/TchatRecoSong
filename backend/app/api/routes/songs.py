from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.crud import song as crud_song
from app.database.connection import get_db
from app.schemas.song import SongCreate, SongOut
from app.services.auth import require_admin
from app.utils.rate_limit import limiter

router = APIRouter()


@router.post("/", response_model=SongOut, dependencies=[Depends(require_admin)])
def add_song(song: SongCreate, db: Session = Depends(get_db)):
    result = crud_song.add_or_increment_song(db, song)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chanson bannie")
    return result


@router.get("/", response_model=list[SongOut])
def list_songs(db: Session = Depends(get_db)):
    return crud_song.get_all_songs(db)


@router.delete(
    "/{song_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_song(song_id: int, db: Session = Depends(get_db)):
    if not crud_song.delete_song(db, song_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chanson introuvable")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{song_id}/vote", response_model=SongOut)
@limiter.limit("20/minute")
def vote_for_song(request: Request, song_id: int, db: Session = Depends(get_db)):
    song = crud_song.increment_vote(db, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chanson introuvable")
    return song
