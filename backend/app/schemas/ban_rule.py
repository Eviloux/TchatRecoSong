from pydantic import BaseModel

class BanRuleCreate(BaseModel):
    title: str = None
    artist: str = None
    link: str = None
