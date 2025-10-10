import sys
from pathlib import Path

import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import ADMIN_JWT_SECRET
from app.database.connection import Base
from app.models.admin_user import AdminUser
from app.services.auth import AdminAuthError, authenticate_email_password
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


def test_authenticate_email_password_success(session: Session) -> None:
    password = "Sup3rSecret!"
    session.add(
        AdminUser(
            email="admin@example.com",
            password_hash=hash_password(password),
            display_name="Admin",
        )
    )
    session.commit()

    token, name = authenticate_email_password(
        session, email="admin@example.com", password=password
    )

    assert name == "Admin"
    payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=["HS256"])
    assert payload["provider"] == "password"
    assert payload["role"] == "admin"


def test_authenticate_email_password_rejects_invalid_password(session: Session) -> None:
    session.add(
        AdminUser(
            email="admin@example.com",
            password_hash=hash_password("Sup3rSecret!"),
        )
    )
    session.commit()

    with pytest.raises(AdminAuthError):
        authenticate_email_password(session, email="admin@example.com", password="wrong")


def test_authenticate_email_password_rejects_inactive_user(session: Session) -> None:
    session.add(
        AdminUser(
            email="admin@example.com",
            password_hash=hash_password("Sup3rSecret!"),
            is_active=False,
        )
    )
    session.commit()

    with pytest.raises(AdminAuthError):
        authenticate_email_password(session, email="admin@example.com", password="Sup3rSecret!")
