"""Briques de sécurité transverses."""

import pytest
from starlette.requests import Request

from app.crud import admin_user as crud_admin_user
from app.models.admin_user import AdminUser
from app.services import admin_user as admin_service
from app.utils import rate_limit
from app.utils.links import InvalidLinkError, normalize_song_link
from app.utils.security import hash_password


def _request(headers: dict[str, str], client_host: str = "10.0.0.1") -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw_headers, "client": (client_host, 1234)})


def test_client_ip_uses_entry_added_by_trusted_proxy(monkeypatch):
    monkeypatch.setattr(rate_limit, "TRUSTED_PROXY_COUNT", 1)
    # La première entrée est forgée par le client : elle doit être ignorée.
    request = _request({"X-Forwarded-For": "1.2.3.4, 203.0.113.7"})
    assert rate_limit.get_client_ip(request) == "203.0.113.7"


def test_client_ip_ignores_forwarded_header_without_trusted_proxy(monkeypatch):
    monkeypatch.setattr(rate_limit, "TRUSTED_PROXY_COUNT", 0)
    request = _request({"X-Forwarded-For": "1.2.3.4"})
    assert rate_limit.get_client_ip(request) == "10.0.0.1"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("youtu.be/abc", ("https://youtu.be/abc", "youtube")),
        ("http://www.youtube.com/watch?v=x#t=1", ("https://www.youtube.com/watch?v=x", "youtube")),
        ("https://open.spotify.com/track/1", ("https://open.spotify.com/track/1", "spotify")),
    ],
)
def test_normalize_song_link(raw, expected):
    assert normalize_song_link(raw) == expected


def test_normalize_song_link_rejects_lookalike_host():
    with pytest.raises(InvalidLinkError):
        normalize_song_link("https://open.spotify.com.evil.example/track/1")


def test_legacy_default_password_account_is_disabled(db_session):
    crud_admin_user.create_user(
        db_session, email="old@example.com", password_hash=hash_password("recoadmin")
    )
    crud_admin_user.create_user(
        db_session, email="ok@example.com", password_hash=hash_password("Long-Unique-Pass-1")
    )

    admin_service.disable_legacy_default_password(db_session)

    states = {u.email: u.is_active for u in db_session.query(AdminUser).all()}
    assert states == {"old@example.com": False, "ok@example.com": True}


def test_no_default_admin_without_explicit_password(db_session, monkeypatch):
    monkeypatch.setattr(admin_service, "ADMIN_DEFAULT_PASSWORD_HASH", None)
    admin_service.ensure_default_admin_user(db_session)
    assert db_session.query(AdminUser).count() == 0


def test_default_admin_created_with_explicit_password(db_session, monkeypatch):
    monkeypatch.setattr(admin_service, "ADMIN_DEFAULT_PASSWORD_HASH", hash_password("S3cret-pass"))
    monkeypatch.setattr(admin_service, "ADMIN_DEFAULT_EMAIL", "boss@example.com")
    admin_service.ensure_default_admin_user(db_session)
    assert crud_admin_user.get_by_email(db_session, "boss@example.com") is not None


def test_security_headers_present(client):
    response = client.get("/health")

    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "max-age" in response.headers["strict-transport-security"]
