from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
import jwt

from jwt import PyJWTError, PyJWK
from jwt.exceptions import MissingRequiredClaimError


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

# Les logs d'authentification doivent apparaître dans la sortie standard de l'application
# même lorsqu'elle est exécutée derrière Uvicorn/Gunicorn.  On rattache donc le logger
# au logger "uvicorn.error" qui est déjà configuré par le serveur HTTP.
logger = logging.getLogger("uvicorn.error").getChild(__name__)


class AdminAuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        super().__init__(status_code=status_code, detail=detail)


def _fetch_google_keys() -> list[dict]:
    global _GOOGLE_KEYS, _GOOGLE_KEYS_EXPIRATION

    now = time.time()
    if _GOOGLE_KEYS and now < _GOOGLE_KEYS_EXPIRATION:
        logger.debug(
            "Utilisation du cache JWKS Google (expire dans %.0fs)",
            _GOOGLE_KEYS_EXPIRATION - now,
        )
        return _GOOGLE_KEYS

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(GOOGLE_JWKS_URL)
            response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - dépend d'un service externe
        logger.exception("Échec lors de la récupération des clés Google")

        raise AdminAuthError("Impossible de vérifier le token Google") from exc

    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - dépend de la réponse Google
        logger.exception("Réponse JWKS Google illisible")

        raise AdminAuthError("Impossible de vérifier le token Google") from exc

    keys = data.get("keys", [])
    logger.debug("%d clés publiques Google récupérées", len(keys))

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
    for jwk_data in keys:
        if jwk_data.get("kid") == kid:
            logger.debug("Clé publique trouvée pour kid=%s", kid)
            try:
                if isinstance(jwk_data, PyJWK):
                    return jwk_data.key

                return PyJWK.from_dict(jwk_data).key

            except (PyJWTError, ValueError, TypeError) as exc:  # pragma: no cover - dépend du format de la clé
                logger.exception("Échec du chargement de la clé Google (kid=%s)", kid)
                raise AdminAuthError("Clé Google invalide") from exc


    logger.warning("Aucune clé Google ne correspond au kid fourni (kid=%s)", kid)
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
    logger.info(
        "Tentative d'authentification Google (kid=%s, alg=%s)",
        kid,
        header.get("alg"),
    )

    public_key = _load_google_public_key(kid)

    try:
        idinfo = jwt.decode(
            credential,
            public_key,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            options={"verify_iss": False},
        )
    except jwt.ExpiredSignatureError:
        logger.info("Token Google expiré pour kid=%s", kid)
        raise AdminAuthError("Token Google expiré")
    except jwt.InvalidAudienceError:
        try:
            claims = jwt.decode(
                credential,
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
                algorithms=["RS256"],
            )
            audience = claims.get("aud")
        except Exception:  # pragma: no cover - best effort logging only
            audience = None
        logger.warning(
            "Audience Google inattendue (attendu=%s, reçu=%s, kid=%s)",
            GOOGLE_CLIENT_ID,
            audience,
            kid,
        )
        raise AdminAuthError("Client Google non autorisé")

    except MissingRequiredClaimError as exc:
        logger.warning(
            "Claim Google manquant (%s) pour kid=%s",
            exc.claim,
            kid,
        )
        raise AdminAuthError("Token Google incomplet") from exc

    except PyJWTError as exc:  # pragma: no cover - dépend du token reçu
        logger.exception("Échec du décodage du token Google (kid=%s)", kid)
        raise AdminAuthError("Token Google invalide") from exc
    except Exception as exc:  # pragma: no cover - sécurité supplémentaire
        logger.exception("Erreur inattendue lors du décodage du token Google (kid=%s)", kid)
        raise AdminAuthError("Impossible de vérifier le token Google") from exc

    if idinfo.get("iss") not in GOOGLE_ISSUERS:
        logger.warning(
            "Émetteur Google invalide (iss=%s, kid=%s)",
            idinfo.get("iss"),
            kid,
        )
        raise AdminAuthError("Émetteur Google invalide")

    email = idinfo.get("email")
    logger.info(
        "Token Google décodé (email=%s, email_verified=%s, iss=%s, aud=%s, sub=%s)",
        email,
        idinfo.get("email_verified"),
        idinfo.get("iss"),
        idinfo.get("aud"),
        idinfo.get("sub"),
    )
    if ALLOWED_GOOGLE_EMAILS and email not in ALLOWED_GOOGLE_EMAILS:
        logger.warning("Email Google non autorisé (email=%s)", email)
        raise AdminAuthError("Adresse non autorisée", status.HTTP_403_FORBIDDEN)

    name = idinfo.get("name") or email or "Google Admin"
    subject = f"google:{idinfo.get('sub')}"
    token = issue_admin_token(subject=subject, name=name, provider="google")
    logger.info("Authentification Google réussie (subject=%s, name=%s)", subject, name)
    return token, name


def authenticate_twitch(access_token: str) -> tuple[str, str]:
    if not TWITCH_CLIENT_ID:
        raise AdminAuthError("TWITCH_CLIENT_ID non configuré")

    headers = {"Authorization": f"OAuth {access_token}", "Client-Id": TWITCH_CLIENT_ID}

    with httpx.Client(timeout=5.0) as client:
        try:
            logger.info("Tentative d'authentification Twitch (OAuth header)")
            response = client.get("https://id.twitch.tv/oauth2/validate", headers=headers)
            if response.status_code == 401:
                # Certains SDK fournissent des tokens à valider via l'entête Bearer
                headers["Authorization"] = f"Bearer {access_token}"
                logger.info(
                    "Réessai de validation Twitch avec l'entête Bearer (statut=%s)",
                    response.status_code,
                )
                response = client.get("https://id.twitch.tv/oauth2/validate", headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - dépend du service externe
            logger.warning(
                "Réponse HTTP inattendue de Twitch (statut=%s, corps=%s)",
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise AdminAuthError("Token Twitch invalide") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - dépend du réseau
            logger.exception("Erreur réseau lors de la validation Twitch")
            raise AdminAuthError("Impossible de contacter Twitch") from exc

    data = response.json()
    login = data.get("login")
    client_id = data.get("client_id")

    logger.info(
        "Token Twitch validé (login=%s, client_id=%s, scopes=%s, expires_in=%s)",
        login,
        client_id,
        data.get("scopes"),
        data.get("expires_in"),
    )

    if client_id != TWITCH_CLIENT_ID:
        logger.warning(
            "Client Twitch inattendu (attendu=%s, reçu=%s)",
            TWITCH_CLIENT_ID,
            client_id,
        )
        raise AdminAuthError("Client Twitch non autorisé")

    if ALLOWED_TWITCH_LOGINS and login not in ALLOWED_TWITCH_LOGINS:
        logger.warning("Compte Twitch non autorisé (login=%s)", login)
        raise AdminAuthError("Compte Twitch non autorisé", status.HTTP_403_FORBIDDEN)

    subject = f"twitch:{data.get('user_id')}"
    name = login or subject
    token = issue_admin_token(subject=subject, name=name, provider="twitch")
    logger.info("Authentification Twitch réussie (subject=%s, name=%s)", subject, name)
    return token, name
