"""Endpoints /ban (réservés aux administrateurs)."""

import pytest

from tests.conftest import TEST_ORIGIN


@pytest.mark.parametrize(
    ("method", "url"),
    [("get", "/ban/"), ("post", "/ban/"), ("put", "/ban/1"), ("delete", "/ban/1")],
)
def test_ban_routes_require_admin(client, method, url):
    response = client.request(method.upper(), url, json={"title": "x"})
    assert response.status_code == 401


def test_create_list_update_delete_rule(client, admin_headers):
    created = client.post("/ban/", json={"title": " Valentine "}, headers=admin_headers)
    assert created.status_code == 200
    rule = created.json()
    assert rule["title"] == "Valentine"

    assert client.get("/ban/", headers=admin_headers).json() == [rule]

    updated = client.put(f"/ban/{rule['id']}", json={"artist": "Maneskin"}, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json() == {"id": rule["id"], "title": None, "artist": "Maneskin", "link": None}

    assert client.delete(f"/ban/{rule['id']}", headers=admin_headers).status_code == 204
    assert client.get("/ban/", headers=admin_headers).json() == []


def test_unknown_rule_returns_404(client, admin_headers):
    assert client.put("/ban/999", json={"title": "x"}, headers=admin_headers).status_code == 404
    assert client.delete("/ban/999", headers=admin_headers).status_code == 404


@pytest.mark.parametrize("payload", [{}, {"title": "   ", "artist": "", "link": None}])
def test_empty_rule_is_rejected(client, admin_headers, payload):
    """Une règle vide correspondrait à toutes les chansons et les supprimerait."""

    response = client.post("/ban/", json=payload, headers=admin_headers)
    assert response.status_code == 422


def test_new_rule_removes_matching_songs_only(client, admin_headers):
    for title, link in (("Valentine", "https://youtu.be/1"), ("Autre", "https://youtu.be/2")):
        client.post(
            "/songs/", json={"title": title, "artist": "A", "link": link}, headers=admin_headers
        )

    client.post("/ban/", json={"title": "valentine"}, headers=admin_headers)

    assert [song["title"] for song in client.get("/songs/").json()] == ["Autre"]


def test_ban_link_is_normalized_like_submitted_links(client, admin_headers):
    response = client.post("/ban/", json={"link": "youtu.be/abc"}, headers=admin_headers)
    assert response.json()["link"] == "https://youtu.be/abc"


def test_cors_preflight_allows_put_for_rule_edition(client):
    response = client.options(
        "/ban/1",
        headers={
            "Origin": TEST_ORIGIN,
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
