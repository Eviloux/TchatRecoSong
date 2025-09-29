import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routes import auth


def test_auth_config_returns_public_ids(monkeypatch):
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "google-id", raising=False)
    monkeypatch.setattr(auth, "TWITCH_CLIENT_ID", "twitch-id", raising=False)

    assert auth.auth_config() == {
        "google_client_id": "google-id",
        "twitch_client_id": "twitch-id",
    }
