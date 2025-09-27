from pydantic import BaseModel


class BanRuleCreate(BaseModel):
    title: str | None = None
    artist: str | None = None
    link: str | None = None


class BanRuleOut(BanRuleCreate):
    id: int

    class Config:
        from_attributes = True
