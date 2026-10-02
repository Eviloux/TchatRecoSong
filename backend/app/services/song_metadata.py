from __future__ import annotations

import html
import json
import logging
import re
from collections.abc import Iterable

import httpx

from app.schemas.song import SongCreate
from app.utils.links import InvalidLinkError, is_https_url, is_trusted_spotify_url, normalize_song_link

LOGGER = logging.getLogger(__name__)

YOUTUBE_OEMBED = "https://www.youtube.com/oembed"
SPOTIFY_OEMBED = "https://open.spotify.com/oembed"
SPOTIFY_BASE_URL = "https://open.spotify.com"

UNKNOWN_TITLE = "Inconnu"
UNKNOWN_ARTIST = "Artiste inconnu"

_SPOTIFY_ARTIST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'"artists"\s*:\s*\[\s*{[^}]*"name"\s*:\s*"(?P<name>[^\"]+)"'),
    re.compile(r'"type"\s*:\s*"artist"[^{}]*"name"\s*:\s*"(?P<name>[^\"]+)"'),
)

_SPOTIFY_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'"type"\s*:\s*"track"[^{}]*"name"\s*:\s*"(?P<name>[^\"]+)"'),
    re.compile(r'"name"\s*:\s*"(?P<name>[^\"]+)"[^{}]*"type"\s*:\s*"track"'),
)


def _decode_json_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return html.unescape(value)


def _first_match(patterns: Iterable[re.Pattern[str]], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _decode_json_string(match.group("name"))
    return None


def _normalize_spotify_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"{SPOTIFY_BASE_URL}{url}"
    return url


def _extract_spotify_metadata_from_html(html_text: str) -> tuple[str | None, str | None]:
    title = _first_match(_SPOTIFY_TITLE_PATTERNS, html_text)
    artist = _first_match(_SPOTIFY_ARTIST_PATTERNS, html_text)
    return title, artist


def _enrich_spotify_metadata(
    client: httpx.Client, result: dict[str, str], link: str
) -> tuple[str, str]:
    title = result.get("title") or UNKNOWN_TITLE
    artist = result.get("author_name")

    if artist:
        return title, artist

    candidate_urls: list[str] = []
    iframe_html = result.get("html") or ""
    for match in re.finditer(r'src="(?P<src>[^"]+)"', iframe_html):
        candidate_urls.append(_normalize_spotify_url(match.group("src")))

    candidate_urls.append(link)

    for candidate in candidate_urls:
        # Le HTML oEmbed vient d'un tiers : on ne suit que des URL Spotify (anti-SSRF).
        if not is_trusted_spotify_url(candidate):
            continue
        try:
            response = client.get(candidate)
            response.raise_for_status()
        except httpx.HTTPError:  # pragma: no cover - depends on external network issues
            continue

        parsed_title, parsed_artist = _extract_spotify_metadata_from_html(response.text)
        if parsed_artist:
            artist = parsed_artist
        if parsed_title:
            title = parsed_title

        if artist:
            break

    return title, artist or UNKNOWN_ARTIST


class MetadataError(RuntimeError):
    """Raised when external providers fail to deliver song metadata."""


def _fetch_oembed(client: httpx.Client, endpoint: str, url: str) -> dict[str, str]:
    response = client.get(endpoint, params={"url": url, "format": "json"})
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise MetadataError("Réponse invalide du fournisseur") from exc
    if not isinstance(payload, dict):
        raise MetadataError("Réponse invalide du fournisseur")
    return payload


def _clean_text(value: object, fallback: str, max_length: int = 500) -> str:
    text = value.strip() if isinstance(value, str) else ""
    return (text or fallback)[:max_length]


def _build_song(
    result: dict[str, str], link: str, *, title: str | None = None, artist: str | None = None
) -> SongCreate:
    thumbnail = result.get("thumbnail_url")
    return SongCreate(
        title=_clean_text(title or result.get("title"), UNKNOWN_TITLE),
        artist=_clean_text(artist or result.get("author_name"), UNKNOWN_ARTIST),
        link=link,
        # Affichée telle quelle dans le front : uniquement en HTTPS.
        thumbnail=thumbnail if is_https_url(thumbnail) and len(thumbnail) <= 2000 else None,
    )


def fetch_song_metadata(link: str) -> SongCreate:
    """Retrieve song metadata from YouTube or Spotify using oEmbed."""

    try:
        link, provider = normalize_song_link(link)
    except InvalidLinkError as exc:
        raise MetadataError(str(exc)) from exc

    endpoint = YOUTUBE_OEMBED if provider == "youtube" else SPOTIFY_OEMBED

    with httpx.Client(timeout=5.0) as client:
        try:
            result = _fetch_oembed(client, endpoint, link)
        except httpx.HTTPStatusError as exc:  # pragma: no cover - depends on external API
            LOGGER.warning("Impossible de récupérer les métadonnées pour %s: %s", link, exc)
            raise MetadataError("Impossible de récupérer les informations de la chanson") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - depends on network
            LOGGER.warning("Erreur réseau pour %s: %s", link, exc)
            raise MetadataError("Erreur réseau lors de la récupération des métadonnées") from exc

        if provider == "spotify":
            title, artist = _enrich_spotify_metadata(client, result, link)
            return _build_song(result, link, title=title, artist=artist)

    return _build_song(result, link)
