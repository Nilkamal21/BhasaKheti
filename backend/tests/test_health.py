import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.db.session import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["phase"] == "Phase 1 - Application Foundation"


def test_health_endpoint(client):
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] in ["ok", "degraded"]
    assert data["phase"] == "Phase 1: Application Foundation"
    assert data["database_connected"] is True
    assert "models" in data

    # Verify that model readiness is not falsely reported as ready
    models = data["models"]
    assert "plant_disease_classifier" in models
    assert "soil_type_classifier" in models
    assert "soil_moisture_classifier" in models

    assert models["plant_disease_classifier"]["status"] == "integrated"
    assert models["soil_type_classifier"]["status"] == "integrated"
    assert models["soil_moisture_classifier"]["status"] == "integrated"


def test_cors_headers(client):
    response = client.options(
        f"{settings.API_V1_STR}/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
