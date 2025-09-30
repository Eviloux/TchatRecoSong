from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.schemas.ban_rule import BanRuleCreate, BanRuleOut, BanRuleUpdate
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


@router.put(
    "/{rule_id}",
    response_model=BanRuleOut,
    dependencies=[Depends(require_admin)],
)
def update_ban_rule(rule_id: int, payload: BanRuleUpdate, db: Session = Depends(get_db)):
    updated = crud_ban.update_ban_rule(db, rule_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle introuvable")
    return updated


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_ban_rule(rule_id: int, db: Session = Depends(get_db)):
    deleted = crud_ban.delete_ban_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle introuvable")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
