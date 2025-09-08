from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.song import SongCreate, SongOut
from app.crud import song as crud_song
from app.database.connection import get_db

router = APIRouter()

@router.post("/", response_model=SongOut)
def add_song(song: SongCreate, db: Session = Depends(get_db)):
    result = crud_song.add_or_increment_song(db, song)
    if result is None:
        raise HTTPException(status_code=400, detail="Chanson bannie")
    return result

@router.get("/", response_model=list[SongOut])
def list_songs(db: Session = Depends(get_db)):
    return crud_song.get_all_songs(db)
