from __future__ import annotations

import logging

from fastapi import APIRouter

from app.config import GOOGLE_CLIENT_ID, TWITCH_CLIENT_ID
from app.services.auth import authenticate_google, authenticate_twitch, AdminAuthError

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


@router.post("/twitch")
def login_twitch(payload: dict) -> dict:
    access_token = payload.get("access_token")
    if not access_token:
        logger.warning("Requête Twitch sans access_token reçu")
        raise AdminAuthError("Token Twitch manquant")
    logger.info("Requête d'authentification Twitch reçue (token ~%d chars)", len(access_token))
    token, name = authenticate_twitch(access_token)
    logger.info("Authentification Twitch terminée pour %s", name)
    return {"token": token, "provider": "twitch", "name": name}


@router.get("/config")
def auth_config() -> dict:
    """Expose les identifiants publics nécessaires aux clients front."""

    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "twitch_client_id": TWITCH_CLIENT_ID,
    }
