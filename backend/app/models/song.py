from sqlalchemy import Column, Integer, String
from app.database.connection import Base

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    artist = Column(String, index=True)
    link = Column(String, unique=True, index=True)
    thumbnail = Column(String, nullable=True)
    votes = Column(Integer, default=1)
