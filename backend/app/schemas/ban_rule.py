
from pydantic import BaseModel, field_validator, model_validator



class BanRuleBase(BaseModel):
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


    @model_validator(mode="before")
    @classmethod
    def _ensure_any_field(cls, data):
        if isinstance(data, dict):
            if not any(data.get(field) for field in ("title", "artist", "link")):
                raise ValueError("Au moins un champ doit être renseigné")
        return data


class BanRuleCreate(BanRuleBase):
    pass


class BanRuleUpdate(BanRuleBase):
    pass


class BanRuleOut(BanRuleBase):
    id: int

    class Config:
        from_attributes = True
