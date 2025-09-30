from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.ban_rule import BanRule
from app.models.song import Song
from app.schemas.ban_rule import BanRuleCreate, BanRuleUpdate
from app.utils.text import normalize


def _matches_rule(song: Song, rule: BanRule) -> bool:
    matches_title = True
    if rule.title:
        matches_title = normalize(song.title) == normalize(rule.title)

    matches_artist = True
    if rule.artist:
        matches_artist = normalize(song.artist) == normalize(rule.artist)

    return matches_title and matches_artist


def _apply_rule_to_existing_songs(db: Session, rule: BanRule) -> None:
    if rule.link:
        (
            db.query(Song)
            .filter(Song.link == rule.link)
            .delete(synchronize_session=False)
        )
        return

    candidates = db.query(Song).all()
    ids_to_delete: list[int] = []
    for song in candidates:
        if _matches_rule(song, rule):
            ids_to_delete.append(song.id)

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

def is_banned(db: Session, title: str, artist: str, link: str):
    if link:
        if db.query(BanRule).filter(BanRule.link == link).first():
            return True

    normalized_title = normalize(title)
    normalized_artist = normalize(artist)

    candidate_rules = (
        db.query(BanRule)
        .filter(or_(BanRule.title.isnot(None), BanRule.artist.isnot(None)))
        .all()
    )

    for rule in candidate_rules:
        matches_title = True
        if rule.title:
            matches_title = normalize(rule.title) == normalized_title

        matches_artist = True
        if rule.artist:
            matches_artist = normalize(rule.artist) == normalized_artist

        if matches_title and matches_artist:
            return True

    return False
