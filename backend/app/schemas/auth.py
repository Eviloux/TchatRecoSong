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


class TwitchCodePayload(BaseModel):
    code: str
    redirect_uri: str

    @field_validator("code")
    @classmethod
    def _ensure_code_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Le code Twitch est requis")
        return value.strip()

    @field_validator("redirect_uri")
    @classmethod
    def _ensure_redirect_uri_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Le redirect_uri est requis")
        return value.strip()


__all__ = ["EmailPasswordLogin", "TwitchCodePayload"]
