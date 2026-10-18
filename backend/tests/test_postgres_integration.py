import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def verify_postgres_connection():
    """Verify PostgreSQL connectivity before running integration tests."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        pytest.fail(
            f"PostgreSQL integration tests require a working database connection: {exc}"
        )


@pytest.mark.integration
def test_postgres_connection():
    response = client.get("/health/database")

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["database"] == "connected"


@pytest.mark.integration
@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/weather/current",
        "/api/v1/weather/daily",
        "/api/v1/weather/trends",
        "/api/v1/weather/cities/compare",
    ],
)
def test_mart_endpoint_returns_valid_response(endpoint):
    response = client.get(endpoint)

    assert response.status_code == 200, (
        f"{endpoint} failed with HTTP {response.status_code}: {response.text}"
    )

    body = response.json()

    assert "count" in body
    assert isinstance(body["count"], int)
    assert body["count"] >= 0

    assert "data" in body
    assert isinstance(body["data"], list)
    assert body["count"] == len(body["data"])


@pytest.mark.integration
def test_current_weather_optional_city_filter():
    response = client.get(
        "/api/v1/weather/daily",
        params={"city": "Manila"},
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["filters"]["city"] == "Manila"

    for row in body["data"]:
        assert row["city"].lower() == "manila"


@pytest.mark.integration
def test_city_comparison_sort_options():
    response = client.get(
        "/api/v1/weather/cities/compare",
        params={"sort_by": "temperature", "order": "desc"},
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["sort"]["sort_by"] == "temperature"
    assert body["sort"]["order"] == "desc"


@pytest.mark.integration
def test_invalid_city_comparison_sort_is_rejected():
    response = client.get(
        "/api/v1/weather/cities/compare",
        params={"sort_by": "invalid"},
    )

    assert response.status_code == 422
