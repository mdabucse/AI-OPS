from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


def test_health_endpoint_returns_ok():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_reads_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://custom:secret@db:5432/custom")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://custom:secret@db:5432/custom"
