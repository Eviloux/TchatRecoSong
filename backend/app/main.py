import logging
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse, RedirectResponse

from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app.config import (
    CORS_ORIGINS,
    FRONTEND_DIST_PATH,
    FRONTEND_INDEX_PATH,

    FRONTEND_SUBMIT_REDIRECT_URL,

    log_environment_configuration,
)
from app.api.routes import songs, ban_rules, public_submissions, auth
from app import models  # noqa: F401 - ensure models are imported before create_all
from app.database.connection import (
    Base,
    SessionLocal,
    check_connection,
    describe_active_database,
    engine,
)
from app.services.admin_user import ensure_default_admin_user

logger = logging.getLogger(__name__)

app = FastAPI(title="Twitch Song Recommender")

app.state.frontend_index_path = FRONTEND_INDEX_PATH
app.state.frontend_dist_path = FRONTEND_DIST_PATH

app.state.frontend_submit_redirect = FRONTEND_SUBMIT_REDIRECT_URL
app.state.frontend_cors_origins = CORS_ORIGINS



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
        session = SessionLocal()
        try:
            ensure_default_admin_user(session)
        finally:
            session.close()

    log_environment_configuration()

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


def _resolve_frontend_index_path() -> Path | None:
    candidate = getattr(app.state, "frontend_index_path", None)
    if candidate is None:
        return None
    return Path(candidate)



def _build_redirect_target(target_path: str) -> str | None:
    submit_redirect = getattr(app.state, "frontend_submit_redirect", None)
    if submit_redirect:
        if target_path == "/submit":
            return submit_redirect

        parsed = urlparse(submit_redirect)
        if parsed.scheme and parsed.netloc:
            base_path = parsed.path.rstrip("/")
            if base_path.endswith("/submit"):
                base_path = base_path[: -len("/submit")]

            segments = [segment for segment in [base_path.strip("/"), target_path.lstrip("/")]
                        if segment]
            new_path = "/" + "/".join(segments) if segments else "/"
            return urlunparse((parsed.scheme, parsed.netloc, new_path, "", "", ""))

        return submit_redirect

    cors_origins = getattr(app.state, "frontend_cors_origins", None) or []
    for origin in cors_origins:
        parsed = urlparse(origin)
        if not (parsed.scheme and parsed.netloc):
            continue

        base = origin.rstrip("/")
        return f"{base}{target_path}"

    return None


def _serve_frontend_index(target_path: str):

    index_path = _resolve_frontend_index_path()

    if index_path is not None and index_path.exists():
        return FileResponse(index_path)

    redirect_url = _build_redirect_target(target_path)
    if redirect_url:
        return RedirectResponse(url=redirect_url, status_code=307)

    raise HTTPException(
        status_code=503,
        detail=(
            "Interface frontend indisponible : le build n'a pas été déployé sur le "
            "serveur backend."
        ),
    )


@app.get("/submit", include_in_schema=False)
@app.get("/submit/", include_in_schema=False)
def serve_submit():

    return _serve_frontend_index("/submit")



@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
def serve_admin():

    return _serve_frontend_index("/admin")



def _mount_frontend_assets() -> None:
    dist_path = getattr(app.state, "frontend_dist_path", None)
    try:
        dist_dir = Path(dist_path) if dist_path is not None else None
    except TypeError:  # pragma: no cover - sécurité supplémentaire
        dist_dir = None

    if not dist_dir or not dist_dir.exists():
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


_mount_frontend_assets()
