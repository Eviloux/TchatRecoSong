import logging
import os
from typing import Dict, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

# Charger .env en local
load_dotenv()

logger = logging.getLogger(__name__)


def _render_url(url_obj: URL, hide_password: bool) -> str:
    """Serialize a SQLAlchemy URL while controlling password masking."""

    try:
        return url_obj.render_as_string(hide_password=hide_password)
    except AttributeError:  # pragma: no cover - fallback for older SQLAlchemy
        legacy_renderer = getattr(url_obj, "__to_string__", None)
        if callable(legacy_renderer):
            return legacy_renderer(hide_password=hide_password)

        if hide_password:
            return str(url_obj)

        # Dernier recours : reconstruction manuelle du DSN sans masquer
        auth = url_obj.username or ""
        if url_obj.password:
            auth = f"{auth}:{url_obj.password}"
        if auth:
            auth += "@"

        host = url_obj.host or ""
        if url_obj.port:
            host = f"{host}:{url_obj.port}"

        database = f"/{url_obj.database}" if url_obj.database else ""
        query = ""
        if url_obj.query:
            query = "?" + "&".join(f"{k}={v}" for k, v in url_obj.query.items())

        return f"{url_obj.drivername}://{auth}{host}{database}{query}"


def _mask_password(url_obj: URL) -> str:
    """Retourne une représentation de l'URL avec mot de passe masqué."""

    return _render_url(url_obj, hide_password=True)


def _format_url_for_log(url_str: str) -> str:
    """Prépare une URL pour les logs en masquant le mot de passe si possible."""

    try:
        return _mask_password(make_url(url_str))
    except ArgumentError:
        return url_str


def _log_plain_password(url_str: str) -> None:
    """Affiche explicitement le mot de passe PostgreSQL pour diagnostic utilisateur."""

    try:
        url_obj = make_url(url_str)
    except ArgumentError:
        logger.warning(
            "Impossible d'extraire le mot de passe depuis l'URL '%s' : format invalide.",
            url_str,
        )
        return

    password = url_obj.password or ""
    if password:
        logger.warning(
            "Mot de passe PostgreSQL utilisé (à retirer une fois le debug terminé) : %s",
            password,
        )
    else:
        logger.warning(
            "Aucun mot de passe PostgreSQL détecté dans l'URL fournie." \
            " Vérifie la variable d'environnement.",
        )


def _format_url_for_log(url_str: str) -> str:
    """Prépare une URL pour les logs en masquant le mot de passe si possible."""

    try:
        return str(_mask_password(make_url(url_str)))
    except ArgumentError:
        return url_str



def _log_plain_password(url_str: str) -> None:
    """Affiche explicitement le mot de passe PostgreSQL pour diagnostic utilisateur."""

    try:
        url_obj = make_url(url_str)
    except ArgumentError:
        logger.warning(
            "Impossible d'extraire le mot de passe depuis l'URL '%s' : format invalide.",
            url_str,
        )
        return

    password = url_obj.password or ""
    if password:
        logger.warning(
            "Mot de passe PostgreSQL utilisé (à retirer une fois le debug terminé) : %s",
            password,
        )
    else:
        logger.warning(
            "Aucun mot de passe PostgreSQL détecté dans l'URL fournie." \
            " Vérifie la variable d'environnement.",
        )



def _connection_snapshot(url_str: str) -> Dict[str, Optional[str]]:
    """Expose les principales infos de connexion sans mot de passe."""

    try:
        url_obj = make_url(url_str)
    except ArgumentError:
        return {"raw_url": url_str}

    return {
        "drivername": url_obj.drivername,
        "username": url_obj.username,
        "host": url_obj.host,
        "port": str(url_obj.port) if url_obj.port is not None else None,
        "database": url_obj.database,
        "query": "&".join(f"{k}={v}" for k, v in url_obj.query.items()) or None,
    }

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

    if url_obj.query.get("channel_binding") == "require":
        logger.warning(
            "Le paramètre channel_binding=require a été retiré de l'URL car il n'est "
            "pas pris en charge par libpq sur Render. Utilise `sslmode=require` seul."
        )
        query = dict(url_obj.query)
        query.pop("channel_binding", None)
        url_obj = url_obj.set(query=query)

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

    return _render_url(url_obj, hide_password=False)


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
    return _render_url(url, hide_password=False)


def _determine_database_url() -> str:
    raw_database_url = os.getenv("DATABASE_URL")
    if raw_database_url:
        logger.info("DATABASE_URL brut fourni: %s", _format_url_for_log(raw_database_url))
        normalized = _normalize_url(raw_database_url)
        if normalized:
            logger.info(
                "DATABASE_URL normalisée utilisée: %s",
                _format_url_for_log(normalized),
            )

            _log_plain_password(normalized)

            return normalized
        raise RuntimeError(
            "La variable `DATABASE_URL` est définie mais invalide. Vérifie l'URL collée "
            "depuis Neon/Render (sans le préfixe `psql` ni les quotes)."
        )

    assembled = _build_url_from_parts()
    if assembled:
        logger.info(
            "DATABASE_URL assemblée à partir des variables individuelles: %s",
            _format_url_for_log(assembled),
        )

        _log_plain_password(assembled)
        return assembled


    raise RuntimeError(
        "La variable `DATABASE_URL` n'est pas définie. Renseigne-la avec l'URL fournie "
        "par Neon ou Render dans les variables d'environnement du service."
    )


DATABASE_URL = _determine_database_url()

logger.info(
    "Connexion PostgreSQL configurée vers %s",
    _format_url_for_log(DATABASE_URL),
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Générateur de sessions DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def describe_active_database() -> Dict[str, Optional[str]]:
    """Retourne les paramètres de connexion utilisés (mot de passe exclu)."""

    snapshot = _connection_snapshot(DATABASE_URL)
    snapshot["url"] = _format_url_for_log(DATABASE_URL)
    return snapshot


def check_connection() -> None:
    """Déclenche une requête simple pour vérifier la connexion PostgreSQL."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        snapshot = describe_active_database()
        logger.error(
            "Échec de connexion à PostgreSQL avec les paramètres %s", snapshot, exc_info=exc
        )
        raise


if __name__ == "__main__":  # pragma: no cover - utilitaire manuel
    try:
        check_connection()
    except OperationalError:
        exit(1)
    print("Connexion PostgreSQL OK")
