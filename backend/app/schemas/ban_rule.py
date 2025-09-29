from pydantic import BaseModel, field_validator


class BanRuleCreate(BaseModel):
    title: str | None = None
    artist: str | None = None
    link: str | None = None

    @field_validator("title", "artist", "link", mode="before")
    @classmethod
    def _empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class BanRuleOut(BanRuleCreate):
    id: int

    class Config:
        from_attributes = True
