import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Charger .env en local
load_dotenv()

DEFAULT_NEON_URL = (
    "postgresql://neondb_owner:npg_ljrtUWJ9o7Cs@"
    "ep-plain-leaf-ag9ynkn2-pooler.c-2.eu-central-1.aws.neon.tech/"
    "neondb?sslmode=require&channel_binding=require"
)

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_NEON_URL)
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL non défini.")

# Remplacer postgres:// par postgresql:// si nécessaire (Render)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Générateur de sessions DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
