"""Endpoints /songs."""

from app.crud import ban_rule as crud_ban
from app.schemas.ban_rule import BanRuleCreate

SONG = {"title": "Titre", "artist": "Artiste", "link": "https://youtu.be/abc"}


def _create(client, admin_headers, **overrides):
    response = client.post("/songs/", json={**SONG, **overrides}, headers=admin_headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_list_songs_is_public_and_sorted_by_votes(client, admin_headers):
    first = _create(client, admin_headers, link="https://youtu.be/1", title="Un")
    second = _create(client, admin_headers, link="https://youtu.be/2", title="Deux")
    client.post(f"/songs/{second['id']}/vote")

    response = client.get("/songs/")

    assert response.status_code == 200
    assert [song["id"] for song in response.json()] == [second["id"], first["id"]]


def test_add_song_requires_admin(client):
    assert client.post("/songs/", json=SONG).status_code == 401


def test_add_song_rejects_forged_token(client):
    headers = {"Authorization": "Bearer not-a-jwt"}
    assert client.post("/songs/", json=SONG, headers=headers).status_code == 401


def test_add_song_twice_increments_votes(client, admin_headers):
    _create(client, admin_headers)
    assert _create(client, admin_headers)["votes"] == 2


def test_add_song_rejects_javascript_link(client, admin_headers):
    response = client.post(
        "/songs/", json={**SONG, "link": "javascript:alert(1)"}, headers=admin_headers
    )
    assert response.status_code == 422


def test_add_song_rejects_non_https_thumbnail(client, admin_headers):
    response = client.post(
        "/songs/", json={**SONG, "thumbnail": "data:image/png;base64,AAA"}, headers=admin_headers
    )
    assert response.status_code == 422


def test_add_banned_song_returns_400(client, admin_headers, db_session):
    crud_ban.add_ban_rule(db_session, BanRuleCreate(title="Titre"))
    response = client.post("/songs/", json=SONG, headers=admin_headers)
    assert response.status_code == 400


def test_delete_song(client, admin_headers):
    song = _create(client, admin_headers)

    assert client.delete(f"/songs/{song['id']}").status_code == 401
    assert client.delete(f"/songs/{song['id']}", headers=admin_headers).status_code == 204
    assert client.delete(f"/songs/{song['id']}", headers=admin_headers).status_code == 404
    assert client.get("/songs/").json() == []


def test_vote_increments_and_404_on_unknown(client, admin_headers):
    song = _create(client, admin_headers)

    response = client.post(f"/songs/{song['id']}/vote")
    assert response.status_code == 200
    assert response.json()["votes"] == 2
    assert client.post("/songs/9999/vote").status_code == 404


def test_vote_is_rate_limited_per_client(client, admin_headers):
    song = _create(client, admin_headers)
    url = f"/songs/{song['id']}/vote"
    spammer = {"X-Forwarded-For": "203.0.113.1"}

    statuses = [client.post(url, headers=spammer).status_code for _ in range(21)]

    assert statuses[:20] == [200] * 20
    assert statuses[20] == 429
    # Un autre visiteur n'est pas pénalisé par le spammeur.
    assert client.post(url, headers={"X-Forwarded-For": "203.0.113.2"}).status_code == 200
