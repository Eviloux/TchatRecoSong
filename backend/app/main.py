import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError

from app import models  # noqa: F401 - ensure models are imported before create_all
from app.api.routes import auth, ban_rules, public_submissions, songs
from app.config import (
    CORS_ORIGINS,
    FRONTEND_DIST_PATH,
    FRONTEND_INDEX_PATH,
    FRONTEND_SUBMIT_REDIRECT_URL,
    log_environment_configuration,
)
from app.database.connection import Base, SessionLocal, check_connection, engine
from app.services.admin_user import ensure_default_admin_user
from app.utils.rate_limit import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Vérifie la connexion PostgreSQL sans bloquer le démarrage du backend."""

    log_environment_configuration()
    try:
        check_connection()
    except OperationalError:  # pragma: no cover - dépend de l'env d'exécution
        logger.warning(
            "Le backend démarre sans base de données active : les routes dépendantes "
            "échoueront tant que la connexion n'est pas rétablie."
        )
    else:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            ensure_default_admin_user(session)
    yield


app = FastAPI(title="Twitch Song Recommender", lifespan=lifespan)
app.state.limiter = limiter
app.state.frontend_index_path = FRONTEND_INDEX_PATH
app.state.frontend_dist_path = FRONTEND_DIST_PATH
app.state.frontend_submit_redirect = FRONTEND_SUBMIT_REDIRECT_URL
app.state.frontend_cors_origins = CORS_ORIGINS


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Trop de requêtes. Réessaie dans quelques instants."},
    )


# Les erreurs non gérées sont converties ici, *à l'intérieur* du middleware CORS
# (ajouté juste après, donc exécuté avant). Sans cela, Starlette produit la 500
# dans ServerErrorMiddleware, la couche la plus externe : la réponse part sans
# en-têtes CORS et le navigateur affiche une erreur CORS trompeuse, tandis que
# le frontend reçoit une TypeError et croit le backend arrêté.
@app.middleware("http")
async def catch_unhandled_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erreur interne du serveur. Réessaie dans quelques instants."},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # Authentification par en-tête Bearer, aucun cookie : pas besoin de credentials.
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Routes
app.include_router(songs.router, prefix="/songs", tags=["Songs"])
app.include_router(ban_rules.router, prefix="/ban", tags=["BanRules"])
app.include_router(public_submissions.router, prefix="/public/submissions", tags=["PublicSubmissions"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


@app.get("/health", include_in_schema=False)
def health_check() -> dict[str, str]:
    """Endpoint minimal utilisé par le frontend pour vérifier la disponibilité."""

    return {"status": "ok"}


def _build_redirect_target(target_path: str) -> str | None:
    """URL du frontend externe vers laquelle rediriger une page SPA."""

    submit_redirect = getattr(app.state, "frontend_submit_redirect", None)
    if submit_redirect:
        if target_path == "/submit":
            return submit_redirect

        parsed = urlparse(submit_redirect)
        if not (parsed.scheme and parsed.netloc):
            return submit_redirect

        base_path = parsed.path.rstrip("/").removesuffix("/submit")
        segments = [seg for seg in (base_path.strip("/"), target_path.lstrip("/")) if seg]
        new_path = "/" + "/".join(segments)
        return urlunparse((parsed.scheme, parsed.netloc, new_path, "", "", ""))

    for origin in getattr(app.state, "frontend_cors_origins", None) or []:
        parsed = urlparse(origin)
        if parsed.scheme and parsed.netloc:
            return f"{origin.rstrip('/')}{target_path}"

    return None


def _serve_frontend_index(target_path: str):
    index_path = getattr(app.state, "frontend_index_path", None)
    if index_path is not None and Path(index_path).exists():
        return FileResponse(index_path)

    redirect_url = _build_redirect_target(target_path)
    if redirect_url:
        return RedirectResponse(url=redirect_url, status_code=307)

    raise HTTPException(
        status_code=503,
        detail="Interface frontend indisponible : le build n'a pas été déployé sur le serveur backend.",
    )


def _register_spa_route(path: str, *aliases: str) -> None:
    def serve_spa():
        return _serve_frontend_index(path)

    for alias in (path, *aliases):
        app.add_api_route(alias, serve_spa, methods=["GET"], include_in_schema=False)


_register_spa_route("/", "/index.html")
for _page in ("/submit", "/admin", "/login"):
    _register_spa_route(_page, f"{_page}/")


def _mount_frontend_assets() -> None:
    dist_path = getattr(app.state, "frontend_dist_path", None)
    if dist_path is None:
        return

    assets_dir = Path(dist_path) / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


_mount_frontend_assets()
