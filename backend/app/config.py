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


def _format_env_value(value: str | None, mask: bool = False) -> str:
    if value is None:
        return "<non défini>"
    if mask:
        return _mask_secret(value) or "<non défini>"
    return value


def _log_env_value(
    name: str,
    value: str | None,
    mask: bool = False,
    *,
    target_logger: logging.Logger | None = None,
) -> None:
    active_logger = target_logger or logger
    active_logger.info("%s (env): %s", name, _format_env_value(value, mask=mask))



def _log_collection(
    name: str,
    values: Iterable[str],
    *,
    target_logger: logging.Logger | None = None,
) -> None:
    values_list = list(values)
    active_logger = target_logger or logger
    if values_list:
        active_logger.info("%s interprétée: %s", name, values_list)
    else:
        active_logger.info("%s interprétée: <vide>", name)


# Liste des origines autorisées pour CORS
_default_cors = "https://tchatrecosong-front.onrender.com,http://localhost:5173"
_raw_cors_env = os.getenv("CORS_ORIGINS")
_cors_used_default = _raw_cors_env is None
_raw_cors = _raw_cors_env or _default_cors

CORS_ORIGINS = _split_env(_raw_cors)

# Authentification administrateur
_default_admin_secret = "super-secret-change-me"
_raw_admin_secret_env = os.getenv("ADMIN_JWT_SECRET")
_admin_secret_used_default = _raw_admin_secret_env is None
ADMIN_JWT_SECRET = _raw_admin_secret_env or _default_admin_secret

_raw_admin_ttl_env = os.getenv("ADMIN_TOKEN_TTL_MINUTES")
_admin_ttl_used_default = _raw_admin_ttl_env is None
_raw_admin_ttl = _raw_admin_ttl_env or "720"
ADMIN_TOKEN_TTL_MINUTES = int(_raw_admin_ttl)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")

_raw_allowed_google = os.getenv("ALLOWED_GOOGLE_EMAILS", "")
ALLOWED_GOOGLE_EMAILS = set(_split_env(_raw_allowed_google))

_raw_allowed_twitch = os.getenv("ALLOWED_TWITCH_LOGINS", "")
ALLOWED_TWITCH_LOGINS = set(_split_env(_raw_allowed_twitch))


def log_environment_configuration() -> None:
    """Journalise la configuration issue des variables d'environnement."""

    uvicorn_logger = logging.getLogger("uvicorn.error")
    root_logger = logging.getLogger()
    if uvicorn_logger.handlers or uvicorn_logger.hasHandlers():
        active_logger = uvicorn_logger
    elif root_logger.handlers:
        active_logger = root_logger
    else:
        active_logger = logger

    _log_env_value("CORS_ORIGINS", _raw_cors_env, target_logger=active_logger)
    if _cors_used_default:
        active_logger.info(
            "CORS_ORIGINS non définie, utilisation de la valeur par défaut: %s",
            _default_cors,
        )
    _log_collection("CORS_ORIGINS", CORS_ORIGINS, target_logger=active_logger)

    _log_env_value(
        "ADMIN_JWT_SECRET",
        _raw_admin_secret_env,
        mask=True,
        target_logger=active_logger,
    )
    if _admin_secret_used_default:
        active_logger.info(
            "ADMIN_JWT_SECRET non définie, utilisation de la valeur par défaut: %s",
            _mask_secret(_default_admin_secret),
        )

    _log_env_value(
        "ADMIN_TOKEN_TTL_MINUTES",
        _raw_admin_ttl_env,
        target_logger=active_logger,
    )
    if _admin_ttl_used_default:
        active_logger.info(
            "ADMIN_TOKEN_TTL_MINUTES non définie, valeur par défaut: 720"
        )

    _log_env_value("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID, target_logger=active_logger)

    _log_env_value("TWITCH_CLIENT_ID", TWITCH_CLIENT_ID, target_logger=active_logger)

    _log_env_value(
        "ALLOWED_GOOGLE_EMAILS",
        _raw_allowed_google,
        target_logger=active_logger,
    )
    _log_collection(
        "ALLOWED_GOOGLE_EMAILS",
        sorted(ALLOWED_GOOGLE_EMAILS),
        target_logger=active_logger,
    )

    _log_env_value(
        "ALLOWED_TWITCH_LOGINS",
        _raw_allowed_twitch,
        target_logger=active_logger,
    )
    _log_collection(
        "ALLOWED_TWITCH_LOGINS",
        sorted(ALLOWED_TWITCH_LOGINS),
        target_logger=active_logger,
    )

