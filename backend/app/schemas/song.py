from pydantic import BaseModel

class SongCreate(BaseModel):
    title: str
    artist: str
    link: str
    thumbnail: str | None = None
    comment: str | None = None

class SongOut(SongCreate):
    id: int
    votes: int

    class Config:
        from_attributes = True
