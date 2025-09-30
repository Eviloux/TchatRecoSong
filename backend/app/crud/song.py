from sqlalchemy.orm import Session
from app.models.song import Song
from app.schemas.song import SongCreate
from app.crud import ban_rule
from app.utils.text import normalize

def add_or_increment_song(db: Session, song_data: SongCreate):
    if ban_rule.is_banned(db, song_data.title, song_data.artist, song_data.link):
        return None

    title_norm = normalize(song_data.title)
    artist_norm = normalize(song_data.artist)

    song = None

    if song_data.link:
        song = db.query(Song).filter(Song.link == song_data.link).first()

    if song is None:
        candidates = db.query(Song).all()
        for candidate in candidates:
            if (
                normalize(candidate.title or "") == title_norm
                and normalize(candidate.artist or "") == artist_norm
            ):
                song = candidate
                break

    if song is not None:
        song.votes += 1
    else:
        song = Song(**song_data.model_dump())
        db.add(song)

    db.commit()
    db.refresh(song)
    return song

def get_all_songs(db: Session):
    return db.query(Song).order_by(Song.votes.desc()).all()


def delete_song(db: Session, song_id: int) -> bool:
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        return False

    db.delete(song)
    db.commit()
    return True


def increment_vote(db: Session, song_id: int):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        return None

    song.votes += 1
    db.commit()
    db.refresh(song)
    return song
