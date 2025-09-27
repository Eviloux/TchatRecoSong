from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.config import CORS_ORIGINS
from app.api.routes import songs, ban_rules, public_submissions, auth
from app import models  # noqa: F401 - ensure models are imported before create_all
from app.database.connection import Base, engine

# Créer la DB si elle n’existe pas
try:
    Base.metadata.create_all(bind=engine)
except OperationalError as exc:  # pragma: no cover - dépend de l'env d'exécution
    raise RuntimeError(
        "Connexion à la base de données impossible. Vérifie `DATABASE_URL`/`NEON_DATABASE_URL` "
        "et les identifiants configurés sur Render ou Neon."
    ) from exc

app = FastAPI(title="Twitch Song Recommender")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routes
app.include_router(songs.router, prefix="/songs", tags=["Songs"])
app.include_router(ban_rules.router, prefix="/ban", tags=["BanRules"])
app.include_router(public_submissions.router, prefix="/public/submissions", tags=["PublicSubmissions"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

@app.get("/")
def root():
    return {"message": "Backend prêt !"}
