"""Integration helpers for external services."""

from .song_metadata import MetadataError, fetch_song_metadata

__all__ = ["fetch_song_metadata", "MetadataError"]
