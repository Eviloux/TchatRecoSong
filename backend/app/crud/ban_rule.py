from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.ban_rule import BanRule
from app.models.song import Song
from app.schemas.ban_rule import BanRuleCreate, BanRuleUpdate
from app.utils.text import normalize

_UNKNOWN_ARTIST_NORMALIZED = normalize("Artiste inconnu")


def _normalized_overlap(value_a: str, value_b: str) -> bool:
    if not value_a or not value_b:
        return False
    return value_a in value_b or value_b in value_a


def _matches_rule_values(title: str | None, artist: str | None, rule: BanRule) -> bool:
    song_title_norm = normalize(title or "")
    song_artist_norm = normalize(artist or "")
    rule_title_norm = normalize(rule.title or "")
    rule_artist_norm = normalize(rule.artist or "")

    if rule_title_norm and not _normalized_overlap(rule_title_norm, song_title_norm):
        return False

    if not rule_artist_norm:
        return True

    if song_artist_norm and song_artist_norm != _UNKNOWN_ARTIST_NORMALIZED:
        return _normalized_overlap(rule_artist_norm, song_artist_norm)

    # Artiste inconnu (métadonnées Spotify incomplètes) : on ne peut pas vérifier
    # l'artiste, donc on exige un titre *identique* pour bannir. Ni contournement
    # facile de la règle, ni faux positifs sur un titre partiel.
    return bool(rule_title_norm) and rule_title_norm == song_title_norm


def _matches_rule(song: Song, rule: BanRule) -> bool:
    return _matches_rule_values(song.title, song.artist, rule)


def _apply_rule_to_existing_songs(db: Session, rule: BanRule) -> None:
    if rule.link:
        (
            db.query(Song)
            .filter(Song.link == rule.link)
            .delete(synchronize_session=False)
        )
        return

    ids_to_delete = [song.id for song in db.query(Song).all() if _matches_rule(song, rule)]

    if ids_to_delete:
        (
            db.query(Song)
            .filter(Song.id.in_(ids_to_delete))
            .delete(synchronize_session=False)
        )


def add_ban_rule(db: Session, rule: BanRuleCreate):
    db_rule = BanRule(**rule.model_dump())
    db.add(db_rule)
    db.flush()

    _apply_rule_to_existing_songs(db, db_rule)

    db.commit()
    db.refresh(db_rule)
    return db_rule


def update_ban_rule(db: Session, rule_id: int, payload: BanRuleUpdate):
    db_rule = db.get(BanRule, rule_id)
    if db_rule is None:
        return None

    for field, value in payload.model_dump().items():
        setattr(db_rule, field, value)

    db.flush()
    _apply_rule_to_existing_songs(db, db_rule)

    db.commit()
    db.refresh(db_rule)
    return db_rule


def delete_ban_rule(db: Session, rule_id: int) -> bool:
    db_rule = db.get(BanRule, rule_id)
    if db_rule is None:
        return False

    db.delete(db_rule)
    db.commit()
    return True


def list_ban_rules(db: Session):
    return db.query(BanRule).order_by(BanRule.id.desc()).all()


def is_banned(db: Session, title: str | None, artist: str | None, link: str | None):
    normalized_link = (link or "").strip()
    if normalized_link and db.query(BanRule).filter(BanRule.link == normalized_link).first():
        return True

    candidate_rules = (
        db.query(BanRule)
        .filter(or_(BanRule.title.isnot(None), BanRule.artist.isnot(None)))
        .all()
    )
    return any(_matches_rule_values(title, artist, rule) for rule in candidate_rules)
