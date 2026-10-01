from fastapi.testclient import TestClient

from app.api.routes import public_submissions
from app.config import CORS_ORIGINS
from app.main import app


def test_unhandled_error_keeps_cors_headers(monkeypatch):
    """Une 500 doit garder les en-têtes CORS, sinon le front croit le backend arrêté."""

    def boom(link: str):
        raise RuntimeError("panne inattendue")

    monkeypatch.setattr(public_submissions, "fetch_song_metadata", boom)
    public_submissions.limiter.reset()
    origin = CORS_ORIGINS[0]

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/public/submissions/",
            json={"link": "https://youtu.be/abc"},
            headers={"Origin": origin},
        )

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == origin
    assert "panne inattendue" not in response.text
    assert response.json()["detail"]
