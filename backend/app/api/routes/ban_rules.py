from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.ban_rule import BanRuleCreate, BanRuleOut
from app.crud import ban_rule as crud_ban
from app.database.connection import get_db
from app.services.auth import require_admin

router = APIRouter()

@router.get("/", response_model=list[BanRuleOut])
def list_ban_rules(db: Session = Depends(get_db)):
    return crud_ban.list_ban_rules(db)


@router.post("/", response_model=BanRuleOut, dependencies=[Depends(require_admin)])
def add_ban_rule(rule: BanRuleCreate, db: Session = Depends(get_db)):
    return crud_ban.add_ban_rule(db, rule)
