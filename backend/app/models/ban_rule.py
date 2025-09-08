from sqlalchemy import Column, Integer, String
from app.database.connection import Base

class BanRule(Base):
    __tablename__ = "ban_rules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=True)
    artist = Column(String, index=True, nullable=True)
    link = Column(String, index=True, nullable=True)
