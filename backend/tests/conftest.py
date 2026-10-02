"""Configuration commune : base SQLite jetable, jamais la base de production."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Doit précéder tout import de `app` : load_dotenv() ne surcharge pas les
# variables déjà définies, le .env local est donc ignoré pour ces clés.
_TEST_DB = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["ADMIN_JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["CORS_ORIGINS"] = "https://front.example"
os.environ["ALLOWED_GOOGLE_EMAILS"] = "admin@example.com"
os.environ["ALLOWED_TWITCH_LOGINS"] = "streamer"
os.environ["GOOGLE_CLIENT_ID"] = "google-client-id"
os.environ["TWITCH_CLIENT_ID"] = "twitch-client-id"
os.environ["TWITCH_CLIENT_SECRET"] = "twitch-client-secret"
os.environ["ADMIN_PASSWORD_LOGIN_ENABLED"] = "true"
os.environ["TRUSTED_PROXY_COUNT"] = "1"
for _key in ("ADMIN_DEFAULT_PASSWORD", "ADMIN_DEFAULT_PASSWORD_HASH", "FRONTEND_SUBMIT_REDIRECT_URL"):
    os.environ.pop(_key, None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.connection import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.auth import issue_admin_token  # noqa: E402
from app.utils.rate_limit import limiter  # noqa: E402

TEST_ORIGIN = "https://front.example"


@pytest.fixture(autouse=True)
def _clean_state():
    """Chaque test démarre avec des tables vides et des quotas remis à zéro."""

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    limiter.reset()
    yield


@pytest.fixture
def db_session():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    token = issue_admin_token(subject="local:1", name="Admin", provider="password")
    return {"Authorization": f"Bearer {token}"}
