"""Rate limiter partagé par toutes les routes."""

from __future__ import annotations

from slowapi import Limiter
from starlette.requests import Request

from app.config import TRUSTED_PROXY_COUNT


def get_client_ip(request: Request) -> str:
    """Retourne l'IP réelle du client derrière les proxys de confiance.

    Chaque proxy *ajoute* l'adresse qu'il voit à la fin de ``X-Forwarded-For`` :
    on lit donc l'entrée placée par notre dernier proxy de confiance. Les entrées
    plus à gauche sont contrôlées par le client et ne doivent pas être utilisées.
    Sans cela, derrière Render, tous les visiteurs partagent l'IP du proxy et donc
    le même quota.
    """

    forwarded = request.headers.get("x-forwarded-for")
    if TRUSTED_PROXY_COUNT and forwarded:
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if len(hops) >= TRUSTED_PROXY_COUNT:
            return hops[-TRUSTED_PROXY_COUNT]

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=get_client_ip)

__all__ = ["get_client_ip", "limiter"]
