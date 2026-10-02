import logging
import os
import secrets
from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv

from app.utils.security import hash_password

load_dotenv()

logger = logging.getLogger(__name__)


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


def _log_env_value(name: str, value: str | None) -> None:
    logger.info("%s (env): %s", name, "<non défini>" if value is None else value)


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
if _raw_admin_secret and len(_raw_admin_secret) >= 32:
    ADMIN_JWT_SECRET = _raw_admin_secret
else:
    # Jamais de secret par défaut connu : un secret public permettrait de forger
    # des jetons admin. Un secret aléatoire invalide les sessions à chaque redémarrage.
    logger.warning(
        "ADMIN_JWT_SECRET absent ou trop court (< 32 caractères) : secret aléatoire "
        "généré, les sessions admin seront perdues à chaque redémarrage."
    )
    ADMIN_JWT_SECRET = secrets.token_urlsafe(64)

_raw_admin_ttl = os.getenv("ADMIN_TOKEN_TTL_MINUTES")
ADMIN_TOKEN_TTL_MINUTES = int(_raw_admin_ttl or "720")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

_raw_allowed_google = os.getenv("ALLOWED_GOOGLE_EMAILS", "")
ALLOWED_GOOGLE_EMAILS = {v.lower() for v in _split_env(_raw_allowed_google)}

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

_raw_allowed_twitch = os.getenv("ALLOWED_TWITCH_LOGINS", "")
ALLOWED_TWITCH_LOGINS = {v.lower() for v in _split_env(_raw_allowed_twitch)}

_raw_password_login_enabled = os.getenv("ADMIN_PASSWORD_LOGIN_ENABLED")
PASSWORD_LOGIN_ENABLED = _parse_bool(_raw_password_login_enabled, True)

_raw_default_email = os.getenv("ADMIN_DEFAULT_EMAIL")
ADMIN_DEFAULT_EMAIL = (_raw_default_email or "admin@tchatrecosong.local").strip().lower()

_raw_default_name = os.getenv("ADMIN_DEFAULT_NAME")
ADMIN_DEFAULT_NAME = (_raw_default_name or "Admin local").strip() or ADMIN_DEFAULT_EMAIL

_raw_default_password = os.getenv("ADMIN_DEFAULT_PASSWORD")
_raw_default_password_hash = os.getenv("ADMIN_DEFAULT_PASSWORD_HASH")

# Aucun compte n'est créé sans mot de passe explicite (plus de valeur par défaut).
if _raw_default_password_hash and _raw_default_password_hash.strip():
    ADMIN_DEFAULT_PASSWORD_HASH: str | None = _raw_default_password_hash.strip()
elif _raw_default_password:
    ADMIN_DEFAULT_PASSWORD_HASH = hash_password(_raw_default_password)
else:
    ADMIN_DEFAULT_PASSWORD_HASH = None

# Ancien mot de passe par défaut, publié dans le dépôt : tout compte qui l'utilise
# encore est désactivé au démarrage.
LEGACY_DEFAULT_PASSWORD = "recoadmin"

# Nombre de proxys de confiance (Render = 1) pour retrouver l'IP réelle du client.
TRUSTED_PROXY_COUNT = max(int(os.getenv("TRUSTED_PROXY_COUNT", "1")), 0)


# Frontend build (SPA)
_repo_root = Path(__file__).resolve().parents[2]
_default_frontend_dist = _repo_root / "frontend" / "dist"

_raw_frontend_dist = os.getenv("FRONTEND_DIST_PATH")
if _raw_frontend_dist:
    FRONTEND_DIST_PATH = Path(_raw_frontend_dist).expanduser().resolve()
else:
    FRONTEND_DIST_PATH = _default_frontend_dist

_raw_frontend_index = os.getenv("FRONTEND_INDEX_PATH")
if _raw_frontend_index:
    FRONTEND_INDEX_PATH = Path(_raw_frontend_index).expanduser().resolve()
else:
    FRONTEND_INDEX_PATH = FRONTEND_DIST_PATH / "index.html"


_raw_frontend_submit_redirect = os.getenv("FRONTEND_SUBMIT_REDIRECT_URL")
FRONTEND_SUBMIT_REDIRECT_URL = (
    _raw_frontend_submit_redirect.strip() if _raw_frontend_submit_redirect else None
)



def log_environment_configuration() -> None:
    """Journalise les valeurs brutes et interprétées des variables d'environnement."""

    _log_env_value("CORS_ORIGINS", _raw_cors)
    if _raw_cors is None:
        logger.info(
            "CORS_ORIGINS non définie, utilisation de la valeur par défaut: %s",
            _default_cors,
        )
    _log_collection("CORS_ORIGINS", CORS_ORIGINS)

    logger.info("ADMIN_JWT_SECRET défini: %s", bool(_raw_admin_secret))

    _log_env_value("ADMIN_TOKEN_TTL_MINUTES", _raw_admin_ttl)
    if _raw_admin_ttl is None:
        logger.info("ADMIN_TOKEN_TTL_MINUTES non définie, valeur par défaut: 720")

    _log_env_value("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)

    _log_env_value("ALLOWED_GOOGLE_EMAILS", _raw_allowed_google)
    _log_collection("ALLOWED_GOOGLE_EMAILS", sorted(ALLOWED_GOOGLE_EMAILS))

    _log_env_value("TWITCH_CLIENT_ID", TWITCH_CLIENT_ID)
    logger.info("TWITCH_CLIENT_SECRET défini: %s", bool(TWITCH_CLIENT_SECRET))
    _log_env_value("ALLOWED_TWITCH_LOGINS", _raw_allowed_twitch)
    _log_collection("ALLOWED_TWITCH_LOGINS", sorted(ALLOWED_TWITCH_LOGINS))

    _log_env_value("ADMIN_PASSWORD_LOGIN_ENABLED", _raw_password_login_enabled)
    logger.info(
        "ADMIN_PASSWORD_LOGIN_ENABLED interprétée: %s",
        PASSWORD_LOGIN_ENABLED,
    )

    _log_env_value("ADMIN_DEFAULT_EMAIL", _raw_default_email)
    logger.info("ADMIN_DEFAULT_EMAIL interprétée: %s", ADMIN_DEFAULT_EMAIL)

    _log_env_value("ADMIN_DEFAULT_NAME", _raw_default_name)
    logger.info("ADMIN_DEFAULT_NAME interprétée: %s", ADMIN_DEFAULT_NAME)

    logger.info(
        "Mot de passe du compte admin par défaut fourni: %s",
        ADMIN_DEFAULT_PASSWORD_HASH is not None,
    )
    logger.info("TRUSTED_PROXY_COUNT: %s", TRUSTED_PROXY_COUNT)

    _log_env_value("FRONTEND_DIST_PATH", _raw_frontend_dist)
    logger.info("FRONTEND_DIST_PATH résolue: %s", FRONTEND_DIST_PATH)
    _log_env_value("FRONTEND_INDEX_PATH", _raw_frontend_index)
    logger.info("FRONTEND_INDEX_PATH résolue: %s", FRONTEND_INDEX_PATH)

    _log_env_value("FRONTEND_SUBMIT_REDIRECT_URL", _raw_frontend_submit_redirect)
    if FRONTEND_SUBMIT_REDIRECT_URL:
        logger.info(
            "FRONTEND_SUBMIT_REDIRECT_URL interprétée: %s",
            FRONTEND_SUBMIT_REDIRECT_URL,
        )

