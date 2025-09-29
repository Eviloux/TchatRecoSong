import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.config import CORS_ORIGINS, log_environment_configuration
from app.api.routes import songs, ban_rules, public_submissions, auth
from app import models  # noqa: F401 - ensure models are imported before create_all
from app.database.connection import Base, check_connection, describe_active_database, engine

logger = logging.getLogger(__name__)

app = FastAPI(title="Twitch Song Recommender")


@app.on_event("startup")
async def startup_checks() -> None:
    """Vérifie la connexion PostgreSQL sans bloquer le démarrage du backend."""

    log_environment_configuration()

    try:
        check_connection()
    except OperationalError as exc:  # pragma: no cover - dépend de l'env d'exécution
        snapshot = describe_active_database()
        logger.error(
            "Échec de connexion à PostgreSQL avec les paramètres %s", snapshot, exc_info=exc
        )
        logger.warning(
            "Le backend démarre sans base de données active : les routes dépendantes "
            "échoueront tant que la connexion n'est pas rétablie."
        )
    else:
        Base.metadata.create_all(bind=engine)

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
