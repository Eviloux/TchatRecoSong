"""CRUD helpers for administrator accounts."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser


def get_by_email(db: Session, email: str) -> AdminUser | None:
    normalized = email.strip().lower()
    if not normalized:
        return None

    return (
        db.query(AdminUser)
        .filter(func.lower(AdminUser.email) == normalized)
        .first()
    )


def has_password_users(db: Session) -> bool:
    return (
        db.query(AdminUser)
        .filter(AdminUser.is_active.is_(True))
        .limit(1)
        .first()
        is not None
    )


def create_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
    display_name: str | None = None,
    is_active: bool = True,
) -> AdminUser:
    user = AdminUser(
        email=email.strip().lower(),
        password_hash=password_hash,
        display_name=display_name,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


__all__ = ["get_by_email", "has_password_users", "create_user"]
