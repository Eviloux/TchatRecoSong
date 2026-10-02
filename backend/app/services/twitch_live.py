"""Statut « en live » d'une chaîne Twitch via l'API Helix."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import httpx

from app.config import TWITCH_CHANNEL_LOGIN, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

logger = logging.getLogger(__name__)

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_STREAMS_URL = "https://api.twitch.tv/helix/streams"

# Un appel Twitch par minute au maximum, quel que soit le nombre de visiteurs.
STATUS_TTL_SECONDS = 60
# Après un échec, on réessaie plus tôt sans marteler l'API.
ERROR_TTL_SECONDS = 15


@dataclass(frozen=True)
class LiveStatus:
    # None = statut inconnu (Twitch injoignable ou identifiants absents).
    live: bool | None
    title: str | None = None


class _TwitchLiveClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._app_token: str | None = None
        self._app_token_expires_at = 0.0
        self._status = LiveStatus(live=None)
        self._status_expires_at = 0.0

    def reset(self) -> None:
        with self._lock:
            self._app_token = None
            self._app_token_expires_at = 0.0
            self._status = LiveStatus(live=None)
            self._status_expires_at = 0.0

    def get_status(self) -> LiveStatus:
        if not (TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET):
            return LiveStatus(live=None)

        # Le verrou garantit un seul appel Twitch même si plusieurs visiteurs
        # arrivent en même temps à l'expiration du cache.
        with self._lock:
            now = time.monotonic()
            if now < self._status_expires_at:
                return self._status
            try:
                self._status = self._fetch_status(now)
                self._status_expires_at = now + STATUS_TTL_SECONDS
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                logger.warning("Statut live Twitch indisponible: %s", exc)
                self._status = LiveStatus(live=None)
                self._status_expires_at = now + ERROR_TTL_SECONDS
            return self._status

    def _get_app_token(self, client: httpx.Client, now: float) -> str:
        if self._app_token and now < self._app_token_expires_at:
            return self._app_token

        response = client.post(
            TWITCH_TOKEN_URL,
            data={
                "client_id": TWITCH_CLIENT_ID,
                "client_secret": TWITCH_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._app_token = payload["access_token"]
        # Marge d'une minute avant l'expiration annoncée.
        self._app_token_expires_at = now + max(int(payload.get("expires_in", 3600)) - 60, 60)
        return self._app_token

    def _fetch_status(self, now: float) -> LiveStatus:
        with httpx.Client(timeout=5.0) as client:
            token = self._get_app_token(client, now)
            response = client.get(
                TWITCH_STREAMS_URL,
                params={"user_login": TWITCH_CHANNEL_LOGIN},
                headers={"Authorization": f"Bearer {token}", "Client-Id": TWITCH_CLIENT_ID},
            )
            if response.status_code == 401:
                # Jeton révoqué ou expiré plus tôt que prévu : on le renouvellera.
                self._app_token = None
            response.raise_for_status()

        streams = response.json()["data"]
        if not streams:
            return LiveStatus(live=False)
        return LiveStatus(live=True, title=streams[0].get("title"))


twitch_live = _TwitchLiveClient()

__all__ = ["LiveStatus", "twitch_live"]
