"""Integration helpers for external services."""

from .song_metadata import fetch_song_metadata, MetadataError

__all__ = ["fetch_song_metadata", "MetadataError"]
