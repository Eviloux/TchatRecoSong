import logging
import os
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


from app.utils.security import hash_password


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


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

_raw_allowed_google = os.getenv("ALLOWED_GOOGLE_EMAILS", "")
ALLOWED_GOOGLE_EMAILS = set(_split_env(_raw_allowed_google))

_raw_password_login_enabled = os.getenv("ADMIN_PASSWORD_LOGIN_ENABLED")
PASSWORD_LOGIN_ENABLED = _parse_bool(_raw_password_login_enabled, True)

_raw_default_email = os.getenv("ADMIN_DEFAULT_EMAIL")
ADMIN_DEFAULT_EMAIL = (_raw_default_email or "admin@tchatrecosong.local").strip().lower()

_raw_default_name = os.getenv("ADMIN_DEFAULT_NAME")
ADMIN_DEFAULT_NAME = (_raw_default_name or "Admin local").strip() or ADMIN_DEFAULT_EMAIL

_raw_default_password = os.getenv("ADMIN_DEFAULT_PASSWORD")
_raw_default_password_hash = os.getenv("ADMIN_DEFAULT_PASSWORD_HASH")

_DEFAULT_PASSWORD_SALT = bytes.fromhex("4f8d3b57a9c3e2f1b6d4c7a8f0e1b2c3")
_FALLBACK_PASSWORD = "recoadmin"
_fallback_password_hash = hash_password(_FALLBACK_PASSWORD, salt=_DEFAULT_PASSWORD_SALT)

if _raw_default_password_hash and _raw_default_password_hash.strip():
    ADMIN_DEFAULT_PASSWORD_HASH = _raw_default_password_hash.strip()
    _password_hash_source = "ADMIN_DEFAULT_PASSWORD_HASH"
elif _raw_default_password:
    ADMIN_DEFAULT_PASSWORD_HASH = hash_password(_raw_default_password)
    _password_hash_source = "ADMIN_DEFAULT_PASSWORD"
else:
    ADMIN_DEFAULT_PASSWORD_HASH = _fallback_password_hash
    _password_hash_source = "valeur par défaut"


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

    _log_env_value("ALLOWED_GOOGLE_EMAILS", _raw_allowed_google)
    _log_collection("ALLOWED_GOOGLE_EMAILS", sorted(ALLOWED_GOOGLE_EMAILS))

    _log_env_value("ADMIN_PASSWORD_LOGIN_ENABLED", _raw_password_login_enabled)
    logger.info(
        "ADMIN_PASSWORD_LOGIN_ENABLED interprétée: %s",
        PASSWORD_LOGIN_ENABLED,
    )

    _log_env_value("ADMIN_DEFAULT_EMAIL", _raw_default_email)
    logger.info("ADMIN_DEFAULT_EMAIL interprétée: %s", ADMIN_DEFAULT_EMAIL)

    _log_env_value("ADMIN_DEFAULT_NAME", _raw_default_name)
    logger.info("ADMIN_DEFAULT_NAME interprétée: %s", ADMIN_DEFAULT_NAME)

    if _raw_default_password_hash:
        _log_env_value("ADMIN_DEFAULT_PASSWORD_HASH", _raw_default_password_hash)
    if _raw_default_password:
        _log_env_value("ADMIN_DEFAULT_PASSWORD", "<fournie>", mask=True)
    logger.info(
        "ADMIN_DEFAULT_PASSWORD_HASH utilisée (%s)",
        _password_hash_source,
    )

