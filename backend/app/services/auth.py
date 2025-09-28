from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
import jwt
from jwt import PyJWTError
from jwt.algorithms import RSAAlgorithm
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

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}

_GOOGLE_KEYS: list[dict] | None = None
_GOOGLE_KEYS_EXPIRATION: float = 0.0

bearer_scheme = HTTPBearer(auto_error=False)


class AdminAuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        super().__init__(status_code=status_code, detail=detail)


def _fetch_google_keys() -> list[dict]:
    global _GOOGLE_KEYS, _GOOGLE_KEYS_EXPIRATION

    now = time.time()
    if _GOOGLE_KEYS and now < _GOOGLE_KEYS_EXPIRATION:
        return _GOOGLE_KEYS

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(GOOGLE_JWKS_URL)
            response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - dépend d'un service externe
        raise AdminAuthError("Impossible de vérifier le token Google") from exc

    data = response.json()
    keys = data.get("keys", [])

    cache_control = response.headers.get("cache-control", "")
    match = re.search(r"max-age=(\d+)", cache_control)
    if match:
        ttl = int(match.group(1))
        _GOOGLE_KEYS_EXPIRATION = now + ttl
    else:  # pragma: no cover - dépend des en-têtes Google
        _GOOGLE_KEYS_EXPIRATION = now + 60 * 60

    _GOOGLE_KEYS = keys
    return keys


def _load_google_public_key(kid: str) -> Any:
    keys = _fetch_google_keys()
    for jwk in keys:
        if jwk.get("kid") == kid:
            return RSAAlgorithm.from_jwk(json.dumps(jwk))
    raise AdminAuthError("Clé Google introuvable pour le token fourni")


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

    try:
        header = jwt.get_unverified_header(credential)
    except PyJWTError as exc:  # pragma: no cover - token invalide
        raise AdminAuthError("Token Google mal formé") from exc

    kid = header.get("kid")
    if not kid:
        raise AdminAuthError("Token Google mal formé")

    public_key = _load_google_public_key(kid)

    try:
        idinfo = jwt.decode(
            credential,
            public_key,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            issuer=list(GOOGLE_ISSUERS),
        )
    except jwt.ExpiredSignatureError:
        raise AdminAuthError("Token Google expiré")
    except jwt.InvalidAudienceError:
        raise AdminAuthError("Client Google non autorisé")
    except jwt.InvalidIssuerError:
        raise AdminAuthError("Émetteur Google invalide")
    except PyJWTError as exc:  # pragma: no cover - dépend du token reçu
        raise AdminAuthError("Token Google invalide") from exc

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

    headers = {"Authorization": f"OAuth {access_token}", "Client-Id": TWITCH_CLIENT_ID}

    with httpx.Client(timeout=5.0) as client:
        try:
            response = client.get("https://id.twitch.tv/oauth2/validate", headers=headers)
            if response.status_code == 401:
                # Certains SDK fournissent des tokens à valider via l'entête Bearer
                headers["Authorization"] = f"Bearer {access_token}"
                response = client.get("https://id.twitch.tv/oauth2/validate", headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - dépend du service externe
            raise AdminAuthError("Token Twitch invalide") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - dépend du réseau
            raise AdminAuthError("Impossible de contacter Twitch") from exc

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
