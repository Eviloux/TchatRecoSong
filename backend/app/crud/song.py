from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.song import Song
from app.schemas.song import SongCreate
from app.crud import ban_rule
from app.utils.text import normalize

def add_or_increment_song(db: Session, song_data: SongCreate):
    if ban_rule.is_banned(db, song_data.title, song_data.artist, song_data.link):
        return None

    title_norm = normalize(song_data.title)
    artist_norm = normalize(song_data.artist)

    song = db.query(Song).filter(
        or_(
            Song.link == song_data.link,
            (func.lower(func.replace(func.replace(Song.title, ' ', ''), '-', '')) == title_norm) &
            (func.lower(func.replace(func.replace(Song.artist, ' ', ''), '-', '')) == artist_norm)
        )
    ).first()

    if song:
        song.votes += 1
    else:
        song = Song(**song_data.dict())
        db.add(song)

    db.commit()
    db.refresh(song)
    return song

def get_all_songs(db: Session):
    return db.query(Song).order_by(Song.votes.desc()).all()
