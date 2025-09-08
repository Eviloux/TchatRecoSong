# app/config.py
import os
from dotenv import load_dotenv

# Charger le fichier .env
load_dotenv()

# Base de données
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# CORS (séparés par des virgules dans .env)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
