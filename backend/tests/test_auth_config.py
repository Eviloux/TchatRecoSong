import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routes import auth
from app.database.connection import Base
from app.models.admin_user import AdminUser
from app.utils.security import hash_password


@pytest.fixture()
def session(tmp_path) -> Session:
    db_path = tmp_path / "auth.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_auth_config_returns_public_ids(monkeypatch, session: Session):
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "google-id", raising=False)
    monkeypatch.setattr(auth, "PASSWORD_LOGIN_ENABLED", True, raising=False)

    assert auth.auth_config(db=session) == {
        "google_client_id": "google-id",
        "password_login_enabled": False,
    }


def test_auth_config_reports_password_login_when_user_exists(monkeypatch, session: Session):
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "google-id", raising=False)
    monkeypatch.setattr(auth, "PASSWORD_LOGIN_ENABLED", True, raising=False)

    session.add(
        AdminUser(
            email="admin@example.com",
            password_hash=hash_password("Secret123!"),
            display_name="Admin",
        )
    )
    session.commit()

    result = auth.auth_config(db=session)
    assert result == {
        "google_client_id": "google-id",
        "password_login_enabled": True,
    }
