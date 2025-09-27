from __future__ import annotations

from fastapi import APIRouter

from app.services.auth import authenticate_google, authenticate_twitch, AdminAuthError

router = APIRouter()


@router.post("/google")
def login_google(payload: dict) -> dict:
    credential = payload.get("credential")
    if not credential:
        raise AdminAuthError("Credential Google manquant")
    token, name = authenticate_google(credential)
    return {"token": token, "provider": "google", "name": name}


@router.post("/twitch")
def login_twitch(payload: dict) -> dict:
    access_token = payload.get("access_token")
    if not access_token:
        raise AdminAuthError("Token Twitch manquant")
    token, name = authenticate_twitch(access_token)
    return {"token": token, "provider": "twitch", "name": name}
