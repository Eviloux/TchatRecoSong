from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import issue_admin_token


def test_session_requires_bearer_token():
    with TestClient(app) as client:
        response = client.get("/auth/session")

    assert response.status_code == 401
    assert response.json()["detail"]


def test_session_returns_profile_for_valid_token():
    token = issue_admin_token(subject="admin-123", name="Admin Doe", provider="password")

    with TestClient(app) as client:
        response = client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "subject": "admin-123",
        "name": "Admin Doe",
        "provider": "password",
    }
