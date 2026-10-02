"""Endpoint /twitch/live."""

import httpx
import pytest

from app.services import twitch_live as live_module


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.twitch.tv")
            raise httpx.HTTPStatusError("erreur", request=request, response=None)


@pytest.fixture
def twitch_api(monkeypatch):
    """Simule Twitch ; `streams` est la liste renvoyée par Helix."""

    state = {"streams": [], "token_calls": 0, "stream_calls": 0, "fail": False}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, data):
            state["token_calls"] += 1
            assert data["grant_type"] == "client_credentials"
            return _Response(200, {"access_token": "app-token", "expires_in": 3600})

        def get(self, url, params, headers):
            state["stream_calls"] += 1
            if state["fail"]:
                raise httpx.ConnectError("Twitch injoignable")
            assert params == {"user_login": "music_oceane"}
            assert headers["Authorization"] == "Bearer app-token"
            return _Response(200, {"data": state["streams"]})

    monkeypatch.setattr(live_module.httpx, "Client", FakeClient)
    live_module.twitch_live.reset()
    yield state
    live_module.twitch_live.reset()


def test_live_when_stream_is_running(client, twitch_api):
    twitch_api["streams"] = [{"title": "Je chante pour adoucir ta soirée"}]

    response = client.get("/twitch/live")

    assert response.status_code == 200
    assert response.json() == {
        "channel": "music_oceane",
        "live": True,
        "title": "Je chante pour adoucir ta soirée",
    }


def test_offline_when_no_stream(client, twitch_api):
    assert client.get("/twitch/live").json()["live"] is False


def test_status_is_cached_between_visitors(client, twitch_api):
    for _ in range(5):
        client.get("/twitch/live")

    assert twitch_api["stream_calls"] == 1
    assert twitch_api["token_calls"] == 1


def test_unknown_status_when_twitch_is_down(client, twitch_api):
    twitch_api["fail"] = True

    response = client.get("/twitch/live")

    assert response.status_code == 200
    assert response.json()["live"] is None


def test_unknown_status_without_credentials(client, twitch_api, monkeypatch):
    monkeypatch.setattr(live_module, "TWITCH_CLIENT_SECRET", None)

    assert client.get("/twitch/live").json()["live"] is None
    assert twitch_api["stream_calls"] == 0
