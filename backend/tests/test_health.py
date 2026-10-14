from fastapi.testclient import TestClient

import app.main as main_module

client = TestClient(main_module.app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "Weatherflow API"
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_database_health_when_connected(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        lambda: True,
    )

    response = client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_database_health_when_unavailable(monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    def raise_database_error():
        raise SQLAlchemyError("Simulated database failure")

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        raise_database_error,
    )

    response = client.get("/health/database")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "unavailable"

