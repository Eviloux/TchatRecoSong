from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.ban_rule import BanRule
from app.schemas.ban_rule import BanRuleCreate
from app.utils.text import normalize

def add_ban_rule(db: Session, rule: BanRuleCreate):
    db_rule = BanRule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

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
