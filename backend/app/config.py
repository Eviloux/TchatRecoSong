import logging
import os
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _split_env(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _mask_secret(value: str | None, keep: int = 4) -> str | None:
    if not value:
        return value
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep)


def _log_collection(name: str, values: Iterable[str]) -> None:
    values_list = list(values)
    if values_list:
        logger.info("%s interprétée: %s", name, values_list)
    else:
        logger.info("%s interprétée: <vide>", name)


# Liste des origines autorisées pour CORS
_default_cors = "https://tchatrecosong-front.onrender.com,http://localhost:5173"
_raw_cors = os.getenv("CORS_ORIGINS")
if _raw_cors is None:
    logger.info(
        "CORS_ORIGINS non définie, utilisation de la valeur par défaut: %s",
        _default_cors,
    )
    _raw_cors = _default_cors
else:
    logger.info("CORS_ORIGINS récupérée: %s", _raw_cors)
CORS_ORIGINS = _split_env(_raw_cors)
_log_collection("CORS_ORIGINS", CORS_ORIGINS)

# Authentification administrateur
_raw_admin_secret = os.getenv("ADMIN_JWT_SECRET")
if _raw_admin_secret is None:
    logger.info(
        "ADMIN_JWT_SECRET non définie, utilisation de la valeur par défaut: %s",
        _mask_secret("super-secret-change-me"),
    )
    _raw_admin_secret = "super-secret-change-me"
else:
    logger.info("ADMIN_JWT_SECRET récupéré: %s", _mask_secret(_raw_admin_secret))
ADMIN_JWT_SECRET = _raw_admin_secret

_raw_admin_ttl = os.getenv("ADMIN_TOKEN_TTL_MINUTES")
if _raw_admin_ttl is None:
    logger.info("ADMIN_TOKEN_TTL_MINUTES non définie, valeur par défaut: 720")
    _raw_admin_ttl = "720"
else:
    logger.info("ADMIN_TOKEN_TTL_MINUTES récupérée: %s", _raw_admin_ttl)
ADMIN_TOKEN_TTL_MINUTES = int(_raw_admin_ttl)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
if GOOGLE_CLIENT_ID:
    logger.info("GOOGLE_CLIENT_ID récupéré: %s", GOOGLE_CLIENT_ID)
else:
    logger.info("GOOGLE_CLIENT_ID non défini")

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
if TWITCH_CLIENT_ID:
    logger.info("TWITCH_CLIENT_ID récupéré: %s", TWITCH_CLIENT_ID)
else:
    logger.info("TWITCH_CLIENT_ID non défini")

_raw_allowed_google = os.getenv("ALLOWED_GOOGLE_EMAILS", "")
if _raw_allowed_google:
    logger.info("ALLOWED_GOOGLE_EMAILS récupérée: %s", _raw_allowed_google)
else:
    logger.info("ALLOWED_GOOGLE_EMAILS non définie ou vide")
ALLOWED_GOOGLE_EMAILS = set(_split_env(_raw_allowed_google))
_log_collection("ALLOWED_GOOGLE_EMAILS", sorted(ALLOWED_GOOGLE_EMAILS))

_raw_allowed_twitch = os.getenv("ALLOWED_TWITCH_LOGINS", "")
if _raw_allowed_twitch:
    logger.info("ALLOWED_TWITCH_LOGINS récupérée: %s", _raw_allowed_twitch)
else:
    logger.info("ALLOWED_TWITCH_LOGINS non définie ou vide")
ALLOWED_TWITCH_LOGINS = set(_split_env(_raw_allowed_twitch))
_log_collection("ALLOWED_TWITCH_LOGINS", sorted(ALLOWED_TWITCH_LOGINS))

