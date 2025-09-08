from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.ban_rule import BanRuleCreate
from app.crud import ban_rule as crud_ban
from app.database.connection import get_db

router = APIRouter()

@router.post("/")
def add_ban_rule(rule: BanRuleCreate, db: Session = Depends(get_db)):
    return crud_ban.add_ban_rule(db, rule)
