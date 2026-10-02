"""Administrative user helpers."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import (
    ADMIN_DEFAULT_EMAIL,
    ADMIN_DEFAULT_NAME,
    ADMIN_DEFAULT_PASSWORD_HASH,
    LEGACY_DEFAULT_PASSWORD,
    PASSWORD_LOGIN_ENABLED,
)
from app.crud import admin_user as crud_admin_user
from app.models.admin_user import AdminUser
from app.utils.security import verify_password

logger = logging.getLogger(__name__)


def disable_legacy_default_password(db: Session) -> None:
    """Désactive les comptes utilisant encore l'ancien mot de passe public."""

    for user in db.query(AdminUser).filter(AdminUser.is_active.is_(True)).all():
        if verify_password(LEGACY_DEFAULT_PASSWORD, user.password_hash):
            user.is_active = False
            logger.error(
                "Compte admin %s désactivé : il utilisait le mot de passe par défaut public. "
                "Définis ADMIN_DEFAULT_PASSWORD puis réactive-le en base.",
                user.email,
            )
    db.commit()


def ensure_default_admin_user(db: Session) -> None:
    """Crée le compte admin par défaut si un mot de passe explicite est configuré."""

    if not PASSWORD_LOGIN_ENABLED:
        logger.info("Authentification par mot de passe désactivée : aucun compte par défaut créé")
        return

    disable_legacy_default_password(db)

    if not ADMIN_DEFAULT_PASSWORD_HASH:
        logger.info("Aucun ADMIN_DEFAULT_PASSWORD fourni : pas de compte admin par défaut")
        return

    if crud_admin_user.get_by_email(db, ADMIN_DEFAULT_EMAIL):
        return

    crud_admin_user.create_user(
        db,
        email=ADMIN_DEFAULT_EMAIL,
        password_hash=ADMIN_DEFAULT_PASSWORD_HASH,
        display_name=ADMIN_DEFAULT_NAME,
    )
    logger.info("Compte administrateur par défaut créé (%s)", ADMIN_DEFAULT_EMAIL)


__all__ = ["ensure_default_admin_user", "disable_legacy_default_password"]
