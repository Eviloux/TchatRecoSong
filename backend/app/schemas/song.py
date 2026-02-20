from pydantic import BaseModel, Field


class SongCreate(BaseModel):
    title: str = Field(max_length=500)
    artist: str = Field(max_length=500)
    link: str = Field(max_length=2000)
    thumbnail: str | None = Field(default=None, max_length=2000)
    comment: str | None = Field(default=None, max_length=1000)

class SongOut(SongCreate):
    id: int
    votes: int

    class Config:
        from_attributes = True
