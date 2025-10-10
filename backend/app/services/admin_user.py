"""Administrative user helpers."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import (
    ADMIN_DEFAULT_EMAIL,
    ADMIN_DEFAULT_NAME,
    ADMIN_DEFAULT_PASSWORD_HASH,
    PASSWORD_LOGIN_ENABLED,
)
from app.crud import admin_user as crud_admin_user


logger = logging.getLogger(__name__)


def ensure_default_admin_user(db: Session) -> None:
    """Create the default admin user when password login is enabled."""

    if not PASSWORD_LOGIN_ENABLED:
        logger.info("Authentification par mot de passe désactivée : aucun compte par défaut créé")
        return

    if not ADMIN_DEFAULT_EMAIL or not ADMIN_DEFAULT_PASSWORD_HASH:
        logger.warning(
            "Paramètres de compte administrateur incomplets : email=%s, hash défini=%s",
            ADMIN_DEFAULT_EMAIL,
            bool(ADMIN_DEFAULT_PASSWORD_HASH),
        )
        return

    existing = crud_admin_user.get_by_email(db, ADMIN_DEFAULT_EMAIL)
    if existing:
        logger.debug("Compte administrateur par défaut déjà présent (%s)", existing.email)
        return

    crud_admin_user.create_user(
        db,
        email=ADMIN_DEFAULT_EMAIL,
        password_hash=ADMIN_DEFAULT_PASSWORD_HASH,
        display_name=ADMIN_DEFAULT_NAME,
    )
    logger.info("Compte administrateur par défaut créé (%s)", ADMIN_DEFAULT_EMAIL)


__all__ = ["ensure_default_admin_user"]
