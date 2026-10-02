from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import ban_rule
from app.models.song import Song
from app.schemas.song import SongCreate
from app.utils.text import normalize


def add_or_increment_song(db: Session, song_data: SongCreate):
    if ban_rule.is_banned(db, song_data.title, song_data.artist, song_data.link):
        return None

    title_norm = normalize(song_data.title)
    artist_norm = normalize(song_data.artist)

    song = db.query(Song).filter(Song.link == song_data.link).first()

    if song is None:
        # Comparaison normalisée (accents, casse, ponctuation) : impossible à faire
        # de façon portable en SQL, d'où le filtrage en Python sur les colonnes utiles.
        rows = db.query(Song.id, Song.title, Song.artist).all()
        match_id = next(
            (
                row.id
                for row in rows
                if normalize(row.title or "") == title_norm
                and normalize(row.artist or "") == artist_norm
            ),
            None,
        )
        if match_id is not None:
            song = db.get(Song, match_id)

    if song is not None:
        return increment_vote(db, song.id)

    song = Song(**song_data.model_dump())
    db.add(song)
    try:
        db.commit()
    except IntegrityError:
        # Le même lien vient d'être inséré par une requête concurrente
        # (contrainte UNIQUE) : on compte cette soumission comme un vote.
        db.rollback()
        existing = db.query(Song).filter(Song.link == song_data.link).first()
        if existing is None:
            raise
        return increment_vote(db, existing.id)

    db.refresh(song)
    return song


def get_all_songs(db: Session):
    return db.query(Song).order_by(Song.votes.desc()).all()


def delete_song(db: Session, song_id: int) -> bool:
    song = db.get(Song, song_id)
    if song is None:
        return False

    db.delete(song)
    db.commit()
    return True


def increment_vote(db: Session, song_id: int):
    # Incrément atomique en SQL : pas de vote perdu entre deux requêtes simultanées.
    updated = (
        db.query(Song)
        .filter(Song.id == song_id)
        .update({Song.votes: Song.votes + 1}, synchronize_session=False)
    )
    db.commit()
    if not updated:
        return None
    song = db.get(Song, song_id)
    db.refresh(song)
    return song
