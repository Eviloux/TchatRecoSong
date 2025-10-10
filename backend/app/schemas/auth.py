import re

from pydantic import BaseModel, field_validator


_EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EmailPasswordLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not value or not _EMAIL_REGEX.match(value):
            raise ValueError("Adresse e-mail invalide")
        return value

    @field_validator("password")
    @classmethod
    def _ensure_password_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Le mot de passe est requis")
        return value


__all__ = ["EmailPasswordLogin"]
