import os
from dotenv import load_dotenv

load_dotenv()

# Liste des origines autorisées pour CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
# Convertir en liste si plusieurs séparées par des virgules
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
