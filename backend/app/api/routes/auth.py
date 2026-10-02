from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import GOOGLE_CLIENT_ID, PASSWORD_LOGIN_ENABLED, TWITCH_CLIENT_ID
from app.crud import admin_user as crud_admin_user
from app.database.connection import get_db
from app.schemas.auth import EmailPasswordLogin, GoogleCredentialPayload, TwitchCodePayload
from app.services.auth import (
    AdminAuthError,
    authenticate_email_password,
    authenticate_google,
    authenticate_twitch,
    require_admin,
)
from app.utils.rate_limit import limiter

router = APIRouter()

# Limite les tentatives de connexion (anti brute-force) par IP client.
LOGIN_RATE_LIMIT = "5/minute"


@router.post("/google")
@limiter.limit(LOGIN_RATE_LIMIT)
def login_google(request: Request, payload: GoogleCredentialPayload) -> dict:
    token, name = authenticate_google(payload.credential)
    return {"token": token, "provider": "google", "name": name}


@router.post("/login")
@limiter.limit(LOGIN_RATE_LIMIT)
def login_password(
    request: Request, payload: EmailPasswordLogin, db: Session = Depends(get_db)
) -> dict:
    if not PASSWORD_LOGIN_ENABLED:
        raise AdminAuthError("Connexion par mot de passe désactivée")
    token, name = authenticate_email_password(
        db, email=payload.email, password=payload.password
    )
    return {"token": token, "provider": "password", "name": name}


@router.post("/twitch")
@limiter.limit(LOGIN_RATE_LIMIT)
def login_twitch(request: Request, payload: TwitchCodePayload) -> dict:
    token, name, subject = authenticate_twitch(payload.code, payload.redirect_uri)
    return {"token": token, "provider": "twitch", "name": name, "subject": subject}


@router.get("/config")
def auth_config(db: Session = Depends(get_db)) -> dict:
    """Expose les identifiants publics nécessaires aux clients front."""

    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "twitch_client_id": TWITCH_CLIENT_ID,
        "password_login_enabled": PASSWORD_LOGIN_ENABLED
        and crud_admin_user.has_password_users(db),
    }


@router.get("/session")
def validate_session(payload: dict = Depends(require_admin)) -> dict:
    """Valide un jeton administrateur et renvoie les informations de profil."""

    return {
        "subject": payload.get("sub"),
        "name": payload.get("name"),
        "provider": payload.get("provider"),
    }
