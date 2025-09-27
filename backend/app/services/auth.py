from __future__ import annotations

import jwt
import httpx
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import (
    ADMIN_JWT_SECRET,
    ADMIN_TOKEN_TTL_MINUTES,
    ALLOWED_GOOGLE_EMAILS,
    ALLOWED_TWITCH_LOGINS,
    GOOGLE_CLIENT_ID,
    TWITCH_CLIENT_ID,
)

bearer_scheme = HTTPBearer(auto_error=False)


class AdminAuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        super().__init__(status_code=status_code, detail=detail)


def issue_admin_token(*, subject: str, name: str, provider: str) -> str:
    expiration = datetime.utcnow() + timedelta(minutes=ADMIN_TOKEN_TTL_MINUTES)
    payload = {
        "sub": subject,
        "name": name,
        "provider": provider,
        "role": "admin",
        "exp": expiration,
    }
    return jwt.encode(payload, ADMIN_JWT_SECRET, algorithm="HS256")


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None:
        raise AdminAuthError("Authentification requise")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:  # pragma: no cover - invalid tokens
        raise AdminAuthError("Jeton invalide") from exc

    if payload.get("role") != "admin":
        raise AdminAuthError("Accès refusé", status.HTTP_403_FORBIDDEN)

    return payload


def authenticate_google(credential: str) -> tuple[str, str]:
    if not GOOGLE_CLIENT_ID:
        raise AdminAuthError("GOOGLE_CLIENT_ID non configuré")


    token_info_url = "https://oauth2.googleapis.com/tokeninfo"
    params = {"id_token": credential}
    with httpx.Client(timeout=5.0) as client:
        response = client.get(token_info_url, params=params)

    if response.status_code != 200:  # pragma: no cover - depends on external service
        raise AdminAuthError("Token Google invalide")

    idinfo = response.json()

    audience = idinfo.get("aud")
    if audience != GOOGLE_CLIENT_ID:
        raise AdminAuthError("Client Google non autorisé")

    email = idinfo.get("email")
    if ALLOWED_GOOGLE_EMAILS and email not in ALLOWED_GOOGLE_EMAILS:
        raise AdminAuthError("Adresse non autorisée", status.HTTP_403_FORBIDDEN)

    name = idinfo.get("name") or email or "Google Admin"

    subject = f"google:{idinfo.get('sub')}"
    token = issue_admin_token(subject=subject, name=name, provider="google")
    return token, name


def authenticate_twitch(access_token: str) -> tuple[str, str]:
    if not TWITCH_CLIENT_ID:
        raise AdminAuthError("TWITCH_CLIENT_ID non configuré")

    headers = {"Authorization": f"Bearer {access_token}", "Client-Id": TWITCH_CLIENT_ID}
    with httpx.Client(timeout=5.0) as client:
        response = client.get("https://id.twitch.tv/oauth2/validate", headers=headers)
    if response.status_code != 200:  # pragma: no cover - depends on external service
        raise AdminAuthError("Token Twitch invalide")

    data = response.json()
    login = data.get("login")
    client_id = data.get("client_id")

    if client_id != TWITCH_CLIENT_ID:
        raise AdminAuthError("Client Twitch non autorisé")

    if ALLOWED_TWITCH_LOGINS and login not in ALLOWED_TWITCH_LOGINS:
        raise AdminAuthError("Compte Twitch non autorisé", status.HTTP_403_FORBIDDEN)

    subject = f"twitch:{data.get('user_id')}"
    name = login or subject
    token = issue_admin_token(subject=subject, name=name, provider="twitch")
    return token, name
