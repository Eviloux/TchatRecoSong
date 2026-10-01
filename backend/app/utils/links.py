"""Validation et normalisation des liens de chansons (YouTube / Spotify)."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit, urlunsplit

Provider = Literal["youtube", "spotify"]

_PROVIDER_HOSTS: dict[str, Provider] = {
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    "m.youtube.com": "youtube",
    "youtu.be": "youtube",
    "spotify.com": "spotify",
    "open.spotify.com": "spotify",
}


class InvalidLinkError(ValueError):
    """Lien absent, mal formé ou d'un fournisseur non supporté."""


def normalize_song_link(raw: str) -> tuple[str, Provider]:
    """Retourne le lien en ``https://`` canonique et son fournisseur.

    Seuls les hôtes YouTube/Spotify connus sont acceptés, sans identifiants ni
    port : le lien est ensuite requêté côté serveur, il ne doit donc jamais
    pouvoir viser une autre machine (SSRF).
    """

    cleaned = (raw or "").strip()
    if not cleaned:
        raise InvalidLinkError("Le lien est requis.")

    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"

    parts = urlsplit(cleaned)
    host = (parts.hostname or "").lower()
    provider = _PROVIDER_HOSTS.get(host)
    if (
        parts.scheme.lower() not in {"http", "https"}
        or provider is None
        or parts.username is not None
        or parts.password is not None
        or parts.port is not None
        or not parts.path.strip("/")
    ):
        raise InvalidLinkError("Seuls les liens YouTube et Spotify sont autorisés.")

    return urlunsplit(("https", host, parts.path, parts.query, "")), provider


def is_trusted_spotify_url(url: str) -> bool:
    """Vrai si *url* pointe en HTTPS vers open.spotify.com."""

    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname == "open.spotify.com" and parts.port is None


def is_https_url(url: str | None) -> bool:
    return bool(url) and urlsplit(url).scheme == "https"


__all__ = [
    "InvalidLinkError",
    "Provider",
    "is_https_url",
    "is_trusted_spotify_url",
    "normalize_song_link",
]
