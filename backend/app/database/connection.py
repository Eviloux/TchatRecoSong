import logging
import os
from typing import Iterable, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import declarative_base, sessionmaker

# Charger .env en local
load_dotenv()

logger = logging.getLogger(__name__)

def _iter_env_candidates() -> Iterable[str]:
    keys = (
        "NEON_DATABASE_URL",
        "DATABASE_INTERNAL_URL",
        "DATABASE_URL",
        "DATABASE_EXTERNAL_URL",
        "POSTGRES_INTERNAL_URL",
        "POSTGRES_URL",
    )
    for key in keys:
        value = os.getenv(key)
        if value:
            yield value


def _normalize_host(host: Optional[str]) -> Optional[str]:
    if not host:
        return host
    if "." in host or host in {"localhost", "127.0.0.1"}:
        return host

    fallbacks = (
        os.getenv("DATABASE_INTERNAL_HOST"),
        os.getenv("POSTGRES_INTERNAL_HOST"),
        os.getenv("DATABASE_HOST"),
        os.getenv("POSTGRES_HOST"),
    )
    for candidate in fallbacks:
        if candidate and "." in candidate:
            logger.warning(
                "DATABASE_URL host '%s' ne résout pas : utilisation de '%s' à la place.",
                host,
                candidate,
            )
            return candidate
    return host


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


PLACEHOLDER_TOKENS_IN_URL = (
    ":USER",
    ":USERNAME",
    ":PASSWORD",
    "@HOST",
    ":HOST",
    ":PORT",
    "/DATABASE",
    "/DB",
    "/DBNAME",
)


def _looks_like_template_url(url: str) -> bool:
    upper_url = url.upper()
    return any(token in upper_url for token in PLACEHOLDER_TOKENS_IN_URL)


def _normalize_url(raw_url: str) -> Optional[str]:
    url = raw_url.strip()

    if url.lower().startswith("psql "):
        remainder = url[5:].strip()
        remainder = _strip_quotes(remainder)
        url = remainder

    url = _strip_quotes(url)
    if not url:
        return None

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if _looks_like_template_url(url):
        logger.warning(
            "URL de base de données '%s' ressemble à un gabarit : ignorée."
            " Renseigne les vraies informations de connexion.",
            raw_url,
        )
        return None

    try:
        url_obj = make_url(url)
    except (ArgumentError, ValueError) as exc:  # pragma: no cover - defensive guard
        logger.error(
            "URL de base de données invalide '%s': %s. Vérifie les variables Render/Neon.",
            raw_url,
            exc,
        )
        return None

    normalized_host = _normalize_host(url_obj.host)
    if normalized_host != url_obj.host:
        url_obj = url_obj.set(host=normalized_host)

    sslmode = (
        url_obj.query.get("sslmode")
        or os.getenv("DATABASE_SSLMODE")
        or os.getenv("DATABASE_SSL_MODE")
    )
    if sslmode:
        url_obj = url_obj.set(query={**url_obj.query, "sslmode": sslmode})

    return str(url_obj)


PLACEHOLDER_SETS = {
    "user": {"USER", "USERNAME"},
    "password": {"PASSWORD"},
    "host": {"HOST"},
    "port": {"PORT"},
    "database": {"DATABASE", "DB", "DBNAME"},
}


def _sanitize_part(name: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    stripped = value.strip()
    placeholders = PLACEHOLDER_SETS.get(name, set())
    if stripped.upper() in placeholders:
        logger.warning(
            "La variable %s contient le placeholder '%s' : valeur ignorée.",
            name,
            stripped,
        )
        return None

    return stripped


def _build_url_from_parts() -> Optional[str]:
    user = _sanitize_part(
        "user", os.getenv("DATABASE_USER") or os.getenv("POSTGRES_USER")
    )
    password = _sanitize_part(
        "password",
        os.getenv("DATABASE_PASSWORD") or os.getenv("POSTGRES_PASSWORD"),
    )
    host = _sanitize_part(
        "host",
        (
            os.getenv("DATABASE_INTERNAL_HOST")
            or os.getenv("POSTGRES_INTERNAL_HOST")
            or os.getenv("DATABASE_HOST")
            or os.getenv("POSTGRES_HOST")
        ),
    )
    port = _sanitize_part("port", os.getenv("DATABASE_PORT") or os.getenv("POSTGRES_PORT"))
    database = _sanitize_part(
        "database", os.getenv("DATABASE_NAME") or os.getenv("POSTGRES_DB")
    )

    if not all([user, password, host, database]):
        return None

    host = _normalize_host(host)
    query = {}
    sslmode = os.getenv("DATABASE_SSLMODE") or os.getenv("DATABASE_SSL_MODE")
    if sslmode:
        query["sslmode"] = sslmode
    elif os.getenv("DATABASE_REQUIRE_SSL", "1") != "0":
        query["sslmode"] = "require"

    port_value = None
    if port:
        if port.isdigit():
            port_value = int(port)
        else:
            logger.warning(
                "La valeur de port '%s' n'est pas numérique : port ignoré.",
                port,
            )

    url = URL.create(
        "postgresql",
        username=user,
        password=password,
        host=host,
        port=port_value,
        database=database,
        query=query,
    )
    return str(url)


def _determine_database_url() -> str:
    for value in _iter_env_candidates():
        normalized = _normalize_url(value)
        if normalized:
            return normalized

    assembled = _build_url_from_parts()
    if assembled:
        logger.info("DATABASE_URL assemblée à partir des variables individuelles.")
        return assembled

    raise RuntimeError(
        "Aucune variable de connexion PostgreSQL n'est définie. "
        "Renseigne `NEON_DATABASE_URL`, `DATABASE_URL` ou les champs `DATABASE_*`/`POSTGRES_*` "
        "fournis par Neon ou ton hébergeur."
    )


DATABASE_URL = _determine_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Générateur de sessions DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
