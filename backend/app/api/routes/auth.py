from __future__ import annotations

import logging

from fastapi import APIRouter

from app.config import GOOGLE_CLIENT_ID
from app.services.auth import authenticate_google, AdminAuthError

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


@router.get("/config")
def auth_config() -> dict:
    """Expose les identifiants publics nécessaires aux clients front."""

    return {
        "google_client_id": GOOGLE_CLIENT_ID,
    }
