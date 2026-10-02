from app.api.routes import public_submissions
from tests.conftest import TEST_ORIGIN


def test_unhandled_error_keeps_cors_headers(client, monkeypatch):
    """Une 500 doit garder les en-têtes CORS, sinon le front croit le backend arrêté."""

    def boom(link: str):
        raise RuntimeError("panne inattendue")

    monkeypatch.setattr(public_submissions, "fetch_song_metadata", boom)

    response = client.post(
        "/public/submissions/",
        json={"link": "https://youtu.be/abc"},
        headers={"Origin": TEST_ORIGIN},
    )

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == TEST_ORIGIN
    assert "panne inattendue" not in response.text
    assert response.json()["detail"]
