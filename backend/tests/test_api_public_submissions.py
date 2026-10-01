"""Endpoint public /public/submissions."""

import pytest

from app.api.routes import public_submissions
from app.crud import ban_rule as crud_ban
from app.schemas.ban_rule import BanRuleCreate
from app.schemas.song import SongCreate
from app.services.song_metadata import MetadataError
from tests.conftest import TEST_ORIGIN

URL = "/public/submissions/"


@pytest.fixture
def fetched_links(monkeypatch):
    """Remplace l'appel réseau oEmbed et mémorise les liens demandés."""

    calls: list[str] = []

    def fake_fetch(link: str) -> SongCreate:
        calls.append(link)
        return SongCreate(title="Titre", artist="Artiste", link=link)

    monkeypatch.setattr(public_submissions, "fetch_song_metadata", fake_fetch)
    return calls


def test_submit_creates_song_with_normalized_link(client, fetched_links):
    response = client.post(URL, json={"link": "youtu.be/abc", "comment": "  top  "})

    assert response.status_code == 201
    body = response.json()
    assert body["link"] == "https://youtu.be/abc"
    assert body["comment"] == "top"
    assert body["votes"] == 1
    assert fetched_links == ["https://youtu.be/abc"]


def test_submitting_same_link_counts_as_vote(client, fetched_links):
    client.post(URL, json={"link": "https://youtu.be/abc"})
    response = client.post(URL, json={"link": "https://youtu.be/abc"})

    assert response.status_code == 201
    assert response.json()["votes"] == 2


@pytest.mark.parametrize(
    "link",
    [
        "",
        "https://example.com/watch?v=1",
        "https://youtube.com.evil.example/watch",
        "https://user:pass@youtube.com/watch?v=1",
        "https://youtube.com:8080/watch?v=1",
        "javascript:alert(1)",
        "ftp://youtube.com/watch",
        "https://youtube.com/",
    ],
)
def test_submit_rejects_invalid_links_without_network_call(client, fetched_links, link):
    response = client.post(URL, json={"link": link})

    assert response.status_code == 400
    assert fetched_links == []


def test_submit_rejects_oversized_payload(client, fetched_links):
    response = client.post(URL, json={"link": "https://youtu.be/a", "comment": "x" * 1001})
    assert response.status_code == 422


def test_submit_returns_502_when_metadata_unavailable(client, monkeypatch):
    def failing_fetch(link: str):
        raise MetadataError("Erreur réseau")

    monkeypatch.setattr(public_submissions, "fetch_song_metadata", failing_fetch)

    response = client.post(URL, json={"link": "https://youtu.be/abc"})
    assert response.status_code == 502


def test_submit_banned_song_returns_400(client, fetched_links, db_session):
    crud_ban.add_ban_rule(db_session, BanRuleCreate(link="youtu.be/abc"))

    response = client.post(URL, json={"link": "https://youtu.be/abc"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Chanson bannie"


def test_submit_rate_limit_is_per_client_and_keeps_cors(client, fetched_links):
    viewer_a = {"X-Forwarded-For": "198.51.100.1", "Origin": TEST_ORIGIN}
    viewer_b = {"X-Forwarded-For": "198.51.100.2", "Origin": TEST_ORIGIN}

    for index in range(10):
        response = client.post(URL, json={"link": f"https://youtu.be/{index}"}, headers=viewer_a)
        assert response.status_code == 201

    limited = client.post(URL, json={"link": "https://youtu.be/x"}, headers=viewer_a)
    assert limited.status_code == 429
    assert limited.headers["access-control-allow-origin"] == TEST_ORIGIN

    allowed = client.post(URL, json={"link": "https://youtu.be/y"}, headers=viewer_b)
    assert allowed.status_code == 201
