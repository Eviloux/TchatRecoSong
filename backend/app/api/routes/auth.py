from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import GOOGLE_CLIENT_ID, PASSWORD_LOGIN_ENABLED, TWITCH_CLIENT_ID
from app.crud import admin_user as crud_admin_user
from app.database.connection import get_db
from app.schemas.auth import EmailPasswordLogin, TwitchCodePayload
from app.services.auth import (
    authenticate_email_password,
    authenticate_google,
    authenticate_twitch,
    AdminAuthError,
    require_admin,
)

router = APIRouter()

logger = logging.getLogger("uvicorn.error").getChild(__name__)


@router.post("/google")
def login_google(payload: dict) -> dict:
    credential = payload.get("credential")
    if not credential:
        logger.warning("Requête Google sans credential reçu")
        raise AdminAuthError("Credential Google manquant")
    logger.info("Requête d'authentification Google reçue (credential ~%d chars)", len(credential))
    token, name = authenticate_google(credential)
    logger.info("Authentification Google terminée pour %s", name)
    return {"token": token, "provider": "google", "name": name}


@router.post("/login")
def login_password(
    payload: EmailPasswordLogin, db: Session = Depends(get_db)
) -> dict:
    logger.info("Requête d'authentification locale reçue pour %s", payload.email)
    token, name = authenticate_email_password(
        db, email=payload.email, password=payload.password
    )
    logger.info("Authentification locale terminée pour %s", payload.email)
    return {"token": token, "provider": "password", "name": name}


@router.post("/twitch")
def login_twitch(payload: TwitchCodePayload) -> dict:
    logger.info("Requête d'authentification Twitch reçue")
    token, name, subject = authenticate_twitch(payload.code, payload.redirect_uri)
    logger.info("Authentification Twitch terminée pour %s", name)
    return {"token": token, "provider": "twitch", "name": name, "subject": subject}


@router.get("/config")
def auth_config(db: Session = Depends(get_db)) -> dict:
    """Expose les identifiants publics nécessaires aux clients front."""

    password_enabled = False
    if PASSWORD_LOGIN_ENABLED:
        password_enabled = crud_admin_user.has_password_users(db)

    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "twitch_client_id": TWITCH_CLIENT_ID,
        "password_login_enabled": password_enabled,
    }


@router.get("/session")
def validate_session(payload: dict = Depends(require_admin)) -> dict:
    """Valide un jeton administrateur et renvoie les informations de profil."""

    return {
        "subject": payload.get("sub"),
        "name": payload.get("name"),
        "provider": payload.get("provider"),
    }
