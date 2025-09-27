from __future__ import annotations

import logging
from typing import Dict

import httpx

from app.schemas.song import SongCreate

LOGGER = logging.getLogger(__name__)

YOUTUBE_OEMBED = "https://www.youtube.com/oembed"
SPOTIFY_OEMBED = "https://open.spotify.com/oembed"


class MetadataError(RuntimeError):
    """Raised when external providers fail to deliver song metadata."""


def _fetch_oembed(client: httpx.Client, endpoint: str, url: str) -> Dict[str, str]:
    response = client.get(endpoint, params={"url": url, "format": "json"})
    response.raise_for_status()
    return response.json()


def _build_song(result: Dict[str, str], link: str) -> SongCreate:
    title = result.get("title") or "Inconnu"
    artist = result.get("author_name") or "Artiste inconnu"
    thumbnail = result.get("thumbnail_url")
    return SongCreate(title=title, artist=artist, link=link, thumbnail=thumbnail)


def fetch_song_metadata(link: str) -> SongCreate:
    """Retrieve song metadata from YouTube or Spotify using oEmbed."""

    endpoint: str
    if "youtube" in link or "youtu.be" in link:
        endpoint = YOUTUBE_OEMBED
    elif "spotify" in link:
        endpoint = SPOTIFY_OEMBED
    else:  # pragma: no cover - validated earlier
        raise MetadataError("Lien non supporté")

    with httpx.Client(timeout=5.0) as client:
        try:
            result = _fetch_oembed(client, endpoint, link)
        except httpx.HTTPStatusError as exc:  # pragma: no cover - depends on external API
            LOGGER.warning("Impossible de récupérer les métadonnées pour %s: %s", link, exc)
            raise MetadataError("Impossible de récupérer les informations de la chanson") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - depends on network
            LOGGER.warning("Erreur réseau pour %s: %s", link, exc)
            raise MetadataError("Erreur réseau lors de la récupération des métadonnées") from exc

    if isinstance(result, dict):
        return _build_song(result, link)

    raise MetadataError("Réponse invalide du fournisseur")
