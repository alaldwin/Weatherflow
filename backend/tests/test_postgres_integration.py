import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_postgres_connection():
    response = client.get("/health/database")

    assert response.status_code == 200, response.text
    assert response.json()["database"] == "connected"


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
        f"{endpoint} failed with {response.status_code}: "
        f"{response.text}"
    )

    body = response.json()

    assert "count" in body
    assert isinstance(body["count"], int)
    assert "data" in body
    assert isinstance(body["data"], list)
    assert body["count"] == len(body["data"])


@pytest.mark.integration
def test_current_weather_optional_city_filter():
    response = client.get("/api/v1/weather/daily?city=Manila")

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["filters"]["city"] == "Manila"

    for row in body["data"]:
        assert row["city"].lower() == "manila"


@pytest.mark.integration
def test_city_comparison_sort_options():
    response = client.get(
        "/api/v1/weather/cities/compare"
        "?sort_by=temperature&order=desc"
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["sort"]["sort_by"] == "temperature"
    assert body["sort"]["order"] == "desc"


@pytest.mark.integration
def test_invalid_city_comparison_sort_is_rejected():
    response = client.get(
        "/api/v1/weather/cities/compare?sort_by=invalid"
    )

    assert response.status_code == 422
