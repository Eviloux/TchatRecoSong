from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _require_scheme(value: str | None, schemes: set[str], message: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    parts = urlsplit(cleaned)
    # Ces URL sont rendues dans des href/src côté front : jamais de javascript:, data:…
    if parts.scheme.lower() not in schemes or not parts.netloc:
        raise ValueError(message)
    return cleaned


class SongCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    artist: str = Field(min_length=1, max_length=500)
    link: str = Field(max_length=2000)
    thumbnail: str | None = Field(default=None, max_length=2000)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("link")
    @classmethod
    def _validate_link(cls, value: str) -> str:
        return _require_scheme(value, {"http", "https"}, "Le lien doit être une URL http(s).")

    @field_validator("thumbnail")
    @classmethod
    def _validate_thumbnail(cls, value: str | None) -> str | None:
        return _require_scheme(value, {"https"}, "La miniature doit être une URL https.")


class SongOut(BaseModel):
    """Réponse API : sans validateurs, pour ne pas rejeter d'anciennes lignes en base."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    artist: str | None
    link: str | None
    thumbnail: str | None = None
    comment: str | None = None
    votes: int
