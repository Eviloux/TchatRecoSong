from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.main import app


@contextmanager
def configured_frontend(tmp_path, content: str = "<html><body>SPA ok</body></html>"):
    original_index = getattr(app.state, "frontend_index_path", None)
    original_dist = getattr(app.state, "frontend_dist_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)

    original_cors = getattr(app.state, "frontend_cors_origins", None)


    try:
        index_file = tmp_path / "index.html"
        index_file.write_text(content, encoding="utf-8")
        app.state.frontend_index_path = index_file
        app.state.frontend_dist_path = tmp_path
        app.state.frontend_submit_redirect = None

        app.state.frontend_cors_origins = []

        yield
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_dist_path = original_dist
        app.state.frontend_submit_redirect = original_redirect

        app.state.frontend_cors_origins = original_cors


def test_submit_serves_index_html(tmp_path):
    with configured_frontend(tmp_path):
        with TestClient(app) as client:
            response = client.get("/submit")

        assert response.status_code == 200
        assert "SPA ok" in response.text
        assert response.headers["content-type"].startswith("text/html")


def test_root_serves_index_html(tmp_path):
    with configured_frontend(tmp_path):
        with TestClient(app) as client:
            response = client.get("/")

    assert response.status_code == 200
    assert "SPA ok" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_submit_redirects_when_index_missing():
    original_index = getattr(app.state, "frontend_index_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)
    original_cors = getattr(app.state, "frontend_cors_origins", None)

    try:
        app.state.frontend_index_path = None
        app.state.frontend_submit_redirect = "https://example.com/submit"
        app.state.frontend_cors_origins = []

        with TestClient(app) as client:
            response = client.get("/submit", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/submit"
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_submit_redirect = original_redirect
        app.state.frontend_cors_origins = original_cors


def test_root_redirects_when_index_missing():
    original_index = getattr(app.state, "frontend_index_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)
    original_cors = getattr(app.state, "frontend_cors_origins", None)

    try:
        app.state.frontend_index_path = None
        app.state.frontend_submit_redirect = "https://example.com/submit"
        app.state.frontend_cors_origins = []

        with TestClient(app) as client:
            response = client.get("/", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/"
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_submit_redirect = original_redirect
        app.state.frontend_cors_origins = original_cors


def test_admin_serves_index_html(tmp_path):
    with configured_frontend(tmp_path, content="<html><body>Admin SPA</body></html>"):
        with TestClient(app) as client:
            response = client.get("/admin")

        assert response.status_code == 200
        assert "Admin SPA" in response.text
        assert response.headers["content-type"].startswith("text/html")


def test_admin_with_trailing_slash_serves_index(tmp_path):
    with configured_frontend(tmp_path, content="<html><body>Admin Slash</body></html>"):
        with TestClient(app) as client:
            response = client.get("/admin/")

        assert response.status_code == 200
        assert "Admin Slash" in response.text
        assert response.headers["content-type"].startswith("text/html")


def test_admin_redirects_when_index_missing_with_submit_redirect():
    original_index = getattr(app.state, "frontend_index_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)
    original_cors = getattr(app.state, "frontend_cors_origins", None)

    try:
        app.state.frontend_index_path = None
        app.state.frontend_submit_redirect = "https://example.com/submit"
        app.state.frontend_cors_origins = []

        with TestClient(app) as client:
            response = client.get("/admin", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/admin"
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_submit_redirect = original_redirect
        app.state.frontend_cors_origins = original_cors


def test_login_serves_index_html(tmp_path):
    with configured_frontend(tmp_path, content="<html><body>Login SPA</body></html>"):
        with TestClient(app) as client:
            response = client.get("/login")

        assert response.status_code == 200
        assert "Login SPA" in response.text
        assert response.headers["content-type"].startswith("text/html")


def test_login_with_trailing_slash_serves_index(tmp_path):
    with configured_frontend(tmp_path, content="<html><body>Login Slash</body></html>"):
        with TestClient(app) as client:
            response = client.get("/login/")

        assert response.status_code == 200
        assert "Login Slash" in response.text
        assert response.headers["content-type"].startswith("text/html")


def test_login_redirects_when_index_missing_with_submit_redirect():
    original_index = getattr(app.state, "frontend_index_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)
    original_cors = getattr(app.state, "frontend_cors_origins", None)

    try:
        app.state.frontend_index_path = None
        app.state.frontend_submit_redirect = "https://example.com/submit"
        app.state.frontend_cors_origins = []

        with TestClient(app) as client:
            response = client.get("/login", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/login"
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_submit_redirect = original_redirect
        app.state.frontend_cors_origins = original_cors


def test_redirect_uses_cors_origin_when_no_submit_redirect():
    original_index = getattr(app.state, "frontend_index_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)
    original_cors = getattr(app.state, "frontend_cors_origins", None)

    try:
        app.state.frontend_index_path = None
        app.state.frontend_submit_redirect = None
        app.state.frontend_cors_origins = ["https://front.example"]

        with TestClient(app) as client:
            response = client.get("/submit", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://front.example/submit"
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_submit_redirect = original_redirect
        app.state.frontend_cors_origins = original_cors


def test_root_redirect_uses_cors_origin_when_no_submit_redirect():
    original_index = getattr(app.state, "frontend_index_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)
    original_cors = getattr(app.state, "frontend_cors_origins", None)

    try:
        app.state.frontend_index_path = None
        app.state.frontend_submit_redirect = None
        app.state.frontend_cors_origins = ["https://front.example"]

        with TestClient(app) as client:
            response = client.get("/", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://front.example/"
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_submit_redirect = original_redirect
        app.state.frontend_cors_origins = original_cors

