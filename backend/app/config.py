import os
from dotenv import load_dotenv

load_dotenv()


def _split_env(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


# Liste des origines autorisées pour CORS
CORS_ORIGINS = _split_env(os.getenv("CORS_ORIGINS", ""))

# Authentification administrateur
ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "super-secret-change-me")
ADMIN_TOKEN_TTL_MINUTES = int(os.getenv("ADMIN_TOKEN_TTL_MINUTES", "720"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
ALLOWED_GOOGLE_EMAILS = set(_split_env(os.getenv("ALLOWED_GOOGLE_EMAILS", "")))
ALLOWED_TWITCH_LOGINS = set(_split_env(os.getenv("ALLOWED_TWITCH_LOGINS", "")))

# Requêtes de soumission
SUBMISSION_TTL_MINUTES = int(os.getenv("SUBMISSION_TTL_MINUTES", "5"))
