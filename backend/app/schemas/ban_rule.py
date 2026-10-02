from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.links import InvalidLinkError, normalize_song_link


class BanRuleBase(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    artist: str | None = Field(default=None, max_length=500)
    link: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "artist", "link", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("link")
    @classmethod
    def _normalize_link(cls, value: str | None) -> str | None:
        # Même forme que les liens enregistrés, pour que la règle corresponde.
        if value is None:
            return None
        try:
            return normalize_song_link(value)[0]
        except InvalidLinkError:
            return value

    # Vérifié *après* le nettoyage : une règle sans critère correspondrait à
    # toutes les chansons et les supprimerait toutes.
    @model_validator(mode="after")
    def _ensure_any_field(self) -> "BanRuleBase":
        if not (self.title or self.artist or self.link):
            raise ValueError("Au moins un champ doit être renseigné")
        return self


class BanRuleCreate(BanRuleBase):
    pass


class BanRuleUpdate(BanRuleBase):
    pass


class BanRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None = None
    artist: str | None = None
    link: str | None = None
