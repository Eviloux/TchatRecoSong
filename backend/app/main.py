from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.api.routes import songs, ban_rules
from app.database.connection import Base, engine

# Créer la DB si elle n’existe pas
Base.metadata.create_all(bind=engine)

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

@app.get("/")
def root():
    return {"message": "Backend prêt !"}
