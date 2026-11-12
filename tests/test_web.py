from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.web import mount_frontend


def test_api_aliases_preserve_health_and_decimal_calculation():
    client = TestClient(app)
    assert client.get("/api/health").json() == client.get("/health").json()
    payload = {"base_amount": "0.05", "current_rate_percent": "0", "proposed_rate_percent": "10"}
    assert client.post("/api/simulate", json=payload).json() == client.post("/simulate", json=payload).json()
    assert client.post("/api/simulate", json={**payload, "base_amount": "-1"}).status_code == 422


def test_static_frontend_does_not_expose_server_files_or_hide_api(tmp_path):
    site = tmp_path / "dist"
    site.mkdir()
    (site / "index.html").write_text("<title>Fixture interface</title>", "utf-8")
    (tmp_path / ".env").write_text("Fixture: never public", "utf-8")
    application = FastAPI()

    @application.get("/api/health")
    def health():
        return {"status": "fixture"}

    assert mount_frontend(application, site) is True
    client = TestClient(application)
    assert "Fixture interface" in client.get("/").text
    assert client.get("/api/health").json() == {"status": "fixture"}
    assert client.get("/.env").status_code == 404
    assert client.get("/%2e%2e/.env").status_code == 404
    assert client.get("/app/main.py").status_code == 404


def test_frontend_build_is_optional_for_backend(tmp_path):
    application = FastAPI()
    assert mount_frontend(application, tmp_path / "not-built") is False
    assert TestClient(application).get("/docs").status_code == 200
