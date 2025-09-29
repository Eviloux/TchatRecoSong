import logging
import os
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _split_env(value: str) -> list[str]:
    sanitized = []
    for item in value.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        # Les origines CORS ne doivent pas conserver la barre oblique finale.
        sanitized.append(cleaned.rstrip("/"))
    return sanitized


def _mask_secret(value: str | None, keep: int = 4) -> str | None:
    if not value:
        return value
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep)


def _format_env_value(value: str | None, mask: bool = False) -> str:
    if value is None:
        return "<non défini>"
    if mask:
        return _mask_secret(value) or "<non défini>"
    return value


def _log_env_value(name: str, value: str | None, mask: bool = False) -> None:
    logger.info("%s (env): %s", name, _format_env_value(value, mask=mask))


def _log_collection(name: str, values: Iterable[str]) -> None:
    values_list = list(values)
    if values_list:
        logger.info("%s interprétée: %s", name, values_list)
    else:
        logger.info("%s interprétée: <vide>", name)



# Liste des origines autorisées pour CORS
_default_cors = "https://tchatrecosong-front.onrender.com,http://localhost:5173"

_raw_cors = os.getenv("CORS_ORIGINS")
_effective_cors = _raw_cors if _raw_cors is not None else _default_cors
CORS_ORIGINS = _split_env(_effective_cors)

# Authentification administrateur
_raw_admin_secret = os.getenv("ADMIN_JWT_SECRET")
ADMIN_JWT_SECRET = _raw_admin_secret or "super-secret-change-me"

_raw_admin_ttl = os.getenv("ADMIN_TOKEN_TTL_MINUTES")
ADMIN_TOKEN_TTL_MINUTES = int(_raw_admin_ttl or "720")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")

_raw_allowed_google = os.getenv("ALLOWED_GOOGLE_EMAILS", "")
ALLOWED_GOOGLE_EMAILS = set(_split_env(_raw_allowed_google))

_raw_allowed_twitch = os.getenv("ALLOWED_TWITCH_LOGINS", "")
ALLOWED_TWITCH_LOGINS = set(_split_env(_raw_allowed_twitch))


def log_environment_configuration() -> None:
    """Journalise les valeurs brutes et interprétées des variables d'environnement."""

    _log_env_value("CORS_ORIGINS", _raw_cors)
    if _raw_cors is None:
        logger.info(
            "CORS_ORIGINS non définie, utilisation de la valeur par défaut: %s",
            _default_cors,
        )
    _log_collection("CORS_ORIGINS", CORS_ORIGINS)

    _log_env_value("ADMIN_JWT_SECRET", _raw_admin_secret, mask=True)
    if _raw_admin_secret is None:
        logger.info(
            "ADMIN_JWT_SECRET non définie, utilisation de la valeur par défaut: %s",
            _mask_secret(ADMIN_JWT_SECRET),
        )

    _log_env_value("ADMIN_TOKEN_TTL_MINUTES", _raw_admin_ttl)
    if _raw_admin_ttl is None:
        logger.info("ADMIN_TOKEN_TTL_MINUTES non définie, valeur par défaut: 720")

    _log_env_value("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
    _log_env_value("TWITCH_CLIENT_ID", TWITCH_CLIENT_ID)

    _log_env_value("ALLOWED_GOOGLE_EMAILS", _raw_allowed_google)
    _log_collection("ALLOWED_GOOGLE_EMAILS", sorted(ALLOWED_GOOGLE_EMAILS))

    _log_env_value("ALLOWED_TWITCH_LOGINS", _raw_allowed_twitch)
    _log_collection("ALLOWED_TWITCH_LOGINS", sorted(ALLOWED_TWITCH_LOGINS))

