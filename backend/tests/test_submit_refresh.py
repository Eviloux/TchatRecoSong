from fastapi.testclient import TestClient

from app.main import app


def test_submit_serves_index_html(tmp_path):
    original_index = getattr(app.state, "frontend_index_path", None)
    original_dist = getattr(app.state, "frontend_dist_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)

    try:
        index_file = tmp_path / "index.html"
        index_file.write_text("<html><body>SPA ok</body></html>", encoding="utf-8")

        app.state.frontend_index_path = index_file
        app.state.frontend_dist_path = tmp_path
        app.state.frontend_submit_redirect = None

        with TestClient(app) as client:
            response = client.get("/submit")

            assert response.status_code == 200
            assert "SPA ok" in response.text
            assert response.headers["content-type"].startswith("text/html")
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_dist_path = original_dist
        app.state.frontend_submit_redirect = original_redirect


def test_submit_redirects_when_index_missing(monkeypatch):
    original_index = getattr(app.state, "frontend_index_path", None)
    original_redirect = getattr(app.state, "frontend_submit_redirect", None)

    try:
        app.state.frontend_index_path = None
        app.state.frontend_submit_redirect = "https://example.com/submit"

        with TestClient(app) as client:
            response = client.get("/submit", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/submit"
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_submit_redirect = original_redirect
