from sqlalchemy.orm import Session
from app.models.ban_rule import BanRule
from app.schemas.ban_rule import BanRuleCreate

def add_ban_rule(db: Session, rule: BanRuleCreate):
    db_rule = BanRule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

def is_banned(db: Session, title: str, artist: str, link: str):
    query = db.query(BanRule)
    if title:
        query = query.filter(BanRule.title == title)
    if artist:
        query = query.filter(BanRule.artist == artist)
    if link:
        query = query.filter(BanRule.link == link)
    return db.query(query.exists()).scalar()
