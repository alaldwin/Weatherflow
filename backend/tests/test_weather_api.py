from contextlib import contextmanager
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import (
    city_comparison,
    current_weather,
    daily_weather,
    trends,
)
from app.main import app

client = TestClient(app)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        return FakeResult(self.rows)


class FakeEngine:
    def __init__(self, rows=None, fail=False):
        self.rows = rows or []
        self.fail = fail

    @contextmanager
    def connect(self):
        if self.fail:
            raise SQLAlchemyError("Simulated database failure")
        yield FakeConnection(self.rows)


@pytest.fixture
def weather_row():
    return {
        "city": "Manila",
        "country": "PH",
        "latitude": 14.5995,
        "longitude": 120.9842,
        "temperature": 31.5,
        "feels_like": 35.0,
        "temp_min": 29.0,
        "temp_max": 32.0,
        "humidity": 70,
        "pressure": 1008,
        "visibility": 10000,
        "wind_speed": 3.5,
        "wind_direction": 180,
        "wind_gust": None,
        "cloudiness": 40,
        "weather_main": "Clouds",
        "weather_description": "scattered clouds",
        "weather_icon": "03d",
        "observation_time": datetime(2026, 10, 13, 10, 0),
        "sunrise": None,
        "sunset": None,
        "observation_date": date(2026, 10, 13),
        "avg_temperature": 30.0,
        "min_temperature": 28.0,
        "max_temperature": 32.0,
        "avg_feels_like": 33.0,
        "avg_humidity": 70.0,
        "avg_pressure": 1008.0,
        "avg_wind_speed": 3.5,
        "avg_cloudiness": 40.0,
        "observation_count": 8,
        "previous_avg_temperature": 29.0,
        "temperature_change": 1.0,
        "previous_avg_humidity": 72.0,
        "humidity_change": -2.0,
        "temperature_rank": 1,
        "average_city_temperature": 29.5,
        "difference_from_average": 2.0,
    }


def test_current_weather_list(monkeypatch, weather_row):
    monkeypatch.setattr(
        current_weather,
        "engine",
        FakeEngine([weather_row]),
    )

    response = client.get("/api/v1/weather/current")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["data"][0]["city"] == "Manila"


def test_current_weather_for_city(monkeypatch, weather_row):
    monkeypatch.setattr(
        current_weather,
        "engine",
        FakeEngine([weather_row]),
    )

    response = client.get("/api/v1/weather/current/Manila")

    assert response.status_code == 200
    assert response.json()["city"] == "Manila"


def test_current_weather_city_not_found(monkeypatch):
    monkeypatch.setattr(
        current_weather,
        "engine",
        FakeEngine([]),
    )

    response = client.get("/api/v1/weather/current/Unknown City")

    assert response.status_code == 404


def test_daily_weather(monkeypatch, weather_row):
    monkeypatch.setattr(
        daily_weather,
        "engine",
        FakeEngine([weather_row]),
    )

    response = client.get("/api/v1/weather/daily?city=Manila")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["data"][0]["city"] == "Manila"


def test_daily_weather_rejects_reversed_dates():
    response = client.get(
        "/api/v1/weather/daily?start_date=2026-10-13&end_date=2026-10-01"
    )

    assert response.status_code == 422


def test_weather_trends(monkeypatch, weather_row):
    monkeypatch.setattr(
        trends,
        "engine",
        FakeEngine([weather_row]),
    )

    response = client.get("/api/v1/weather/trends?city=Manila")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_city_comparison(monkeypatch, weather_row):
    monkeypatch.setattr(
        city_comparison,
        "engine",
        FakeEngine([weather_row]),
    )

    response = client.get(
        "/api/v1/weather/cities/compare?sort_by=temperature&order=desc"
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["sort"] == {
        "sort_by": "temperature",
        "order": "desc",
    }


def test_city_comparison_rejects_invalid_sort():
    response = client.get("/api/v1/weather/cities/compare?sort_by=password")

    assert response.status_code == 422


def test_current_weather_database_failure(monkeypatch):
    monkeypatch.setattr(
        current_weather,
        "engine",
        FakeEngine(fail=True),
    )

    response = client.get("/api/v1/weather/current")

    assert response.status_code == 503
