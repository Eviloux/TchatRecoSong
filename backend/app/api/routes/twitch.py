from fastapi import APIRouter

from app.config import TWITCH_CHANNEL_LOGIN
from app.services.twitch_live import twitch_live

router = APIRouter()


@router.get("/live")
def live_status() -> dict:
    """Indique si la chaîne est en direct (``live`` vaut null si inconnu)."""

    status = twitch_live.get_status()
    return {"channel": TWITCH_CHANNEL_LOGIN, "live": status.live, "title": status.title}
