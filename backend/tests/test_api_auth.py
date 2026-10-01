"""Endpoints /auth."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import ADMIN_JWT_SECRET
from app.crud import admin_user as crud_admin_user
from app.services import auth as auth_service
from app.utils.security import hash_password

# --- /auth/session -----------------------------------------------------------

def _token(secret=ADMIN_JWT_SECRET, **claims):
    payload = {
        "sub": "local:1",
        "name": "Admin",
        "provider": "password",
        "role": "admin",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        **claims,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _session(client, token):
    return client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})


def test_session_accepts_valid_token(client):
    response = _session(client, _token())
    assert response.status_code == 200
    assert response.json() == {"subject": "local:1", "name": "Admin", "provider": "password"}


def test_session_rejects_expired_token(client):
    expired = _token(exp=datetime.now(UTC) - timedelta(seconds=1))
    assert _session(client, expired).status_code == 401


def test_session_rejects_token_signed_with_another_secret(client):
    assert _session(client, _token(secret="another-secret-" + "y" * 40)).status_code == 401


def test_session_rejects_unsigned_token(client):
    unsigned = jwt.encode({"sub": "x", "role": "admin"}, key=None, algorithm="none")
    assert _session(client, unsigned).status_code == 401


def test_session_rejects_non_admin_role(client):
    assert _session(client, _token(role="viewer")).status_code == 403


# --- /auth/config ------------------------------------------------------------

def test_config_exposes_only_public_values(client, db_session):
    response = client.get("/auth/config")

    assert response.status_code == 200
    assert response.json() == {
        "google_client_id": "google-client-id",
        "twitch_client_id": "twitch-client-id",
        "password_login_enabled": False,
    }
    assert "secret" not in response.text


# --- /auth/login -------------------------------------------------------------

@pytest.fixture
def password_admin(db_session):
    return crud_admin_user.create_user(
        db_session,
        email="admin@example.com",
        password_hash=hash_password("Correct-Horse-1"),
        display_name="Admin",
    )


def _login(client, email="admin@example.com", password="Correct-Horse-1", ip="192.0.2.1"):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers={"X-Forwarded-For": ip},
    )


def test_login_success_returns_usable_token(client, password_admin):
    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "password"
    assert _session(client, body["token"]).status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [("admin@example.com", "wrong"), ("unknown@example.com", "Correct-Horse-1")],
)
def test_login_failures_share_the_same_message(client, password_admin, email, password):
    response = _login(client, email=email, password=password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Identifiants invalides"


def test_login_rejects_inactive_user(client, password_admin, db_session):
    password_admin.is_active = False
    db_session.commit()
    assert _login(client).status_code == 401


def test_login_rejects_malformed_email(client):
    assert _login(client, email="pas-un-email").status_code == 422


def test_login_is_rate_limited(client, password_admin):
    statuses = [_login(client, password="wrong").status_code for _ in range(6)]

    assert statuses == [401] * 5 + [429]
    assert _login(client, ip="192.0.2.99").status_code == 200


def test_login_disabled_by_configuration(client, password_admin, monkeypatch):
    from app.api.routes import auth as auth_routes

    monkeypatch.setattr(auth_routes, "PASSWORD_LOGIN_ENABLED", False)
    assert _login(client).status_code == 401


# --- /auth/google ------------------------------------------------------------

@pytest.fixture
def google_signer(monkeypatch):
    """Signe de vrais ID tokens RS256 et expose la clé publique au service."""

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(auth_service, "_load_google_public_key", lambda kid: private_key.public_key())

    def sign(**claims):
        payload = {
            "iss": "https://accounts.google.com",
            "aud": "google-client-id",
            "sub": "123",
            "email": "admin@example.com",
            "email_verified": True,
            "name": "Admin Google",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            **claims,
        }
        return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "k1"})

    return sign


def _google(client, credential):
    return client.post("/auth/google", json={"credential": credential})


def test_google_login_success(client, google_signer):
    response = _google(client, google_signer())

    assert response.status_code == 200
    assert response.json()["name"] == "Admin Google"


def test_google_email_comparison_is_case_insensitive(client, google_signer):
    assert _google(client, google_signer(email="Admin@Example.com")).status_code == 200


@pytest.mark.parametrize(
    ("claims", "status"),
    [
        ({"email": "intrus@example.com"}, 403),
        ({"email_verified": False}, 403),
        ({"aud": "autre-client"}, 401),
        ({"iss": "https://evil.example"}, 401),
        ({"exp": datetime.now(UTC) - timedelta(minutes=1)}, 401),
    ],
)
def test_google_login_rejections(client, google_signer, claims, status):
    assert _google(client, google_signer(**claims)).status_code == status


def test_google_empty_allowlist_denies_everyone(client, google_signer, monkeypatch):
    monkeypatch.setattr(auth_service, "ALLOWED_GOOGLE_EMAILS", set())
    assert _google(client, google_signer()).status_code == 403


def test_google_rejects_missing_credential(client):
    assert client.post("/auth/google", json={}).status_code == 422


# --- /auth/twitch ------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


@pytest.fixture
def twitch_user(monkeypatch):
    """Simule l'API Twitch ; le login renvoyé est modifiable par le test."""

    state = {"login": "streamer", "token_status": 200}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, data):
            return _FakeResponse(state["token_status"], {"access_token": "at"})

        def get(self, url, headers):
            user = {"login": state["login"], "id": "42", "display_name": "Streamer"}
            return _FakeResponse(200, {"data": [user]})

    monkeypatch.setattr(auth_service.httpx, "Client", FakeClient)
    return state


def _twitch(client):
    return client.post(
        "/auth/twitch", json={"code": "abc", "redirect_uri": "https://front.example/login"}
    )


def test_twitch_login_success(client, twitch_user):
    response = _twitch(client)

    assert response.status_code == 200
    assert response.json()["subject"] == "twitch:42"


def test_twitch_login_rejects_unknown_account(client, twitch_user):
    twitch_user["login"] = "intrus"
    assert _twitch(client).status_code == 403


def test_twitch_empty_allowlist_denies_everyone(client, twitch_user, monkeypatch):
    monkeypatch.setattr(auth_service, "ALLOWED_TWITCH_LOGINS", set())
    assert _twitch(client).status_code == 403


def test_twitch_invalid_code(client, twitch_user):
    twitch_user["token_status"] = 400
    assert _twitch(client).status_code == 401
