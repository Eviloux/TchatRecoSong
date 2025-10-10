from fastapi.testclient import TestClient

from app.main import app


def test_submit_serves_index_html(tmp_path):
    original_index = getattr(app.state, "frontend_index_path", None)
    original_dist = getattr(app.state, "frontend_dist_path", None)

    try:
        index_file = tmp_path / "index.html"
        index_file.write_text("<html><body>SPA ok</body></html>", encoding="utf-8")

        app.state.frontend_index_path = index_file
        app.state.frontend_dist_path = tmp_path

        with TestClient(app) as client:
            response = client.get("/submit")

            assert response.status_code == 200
            assert "SPA ok" in response.text
            assert response.headers["content-type"].startswith("text/html")
    finally:
        app.state.frontend_index_path = original_index
        app.state.frontend_dist_path = original_dist
