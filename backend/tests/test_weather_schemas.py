from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.schemas.weather import (
    CurrentWeather,
    DailyWeather,
    DateFilters,
)


def test_current_weather_schema_accepts_valid_data():
    weather = CurrentWeather(
        city="Manila",
        country="PH",
        temperature=31.5,
        humidity=70,
        observation_time="2026-10-13T10:00:00",
    )

    assert weather.city == "Manila"
    assert weather.temperature == 31.5
    assert weather.humidity == 70
    assert isinstance(weather.observation_time, datetime)


def test_current_weather_allows_optional_values():
    weather = CurrentWeather(city="Manila")

    assert weather.city == "Manila"
    assert weather.temperature is None
    assert weather.country is None


def test_current_weather_requires_city():
    with pytest.raises(ValidationError):
        CurrentWeather(temperature=31.5)


def test_daily_weather_parses_observation_date():
    daily = DailyWeather(
        city="Cebu City",
        country="PH",
        observation_date="2026-10-13",
        avg_temperature=29.5,
        observation_count=8,
    )

    assert daily.city == "Cebu City"
    assert daily.observation_date == date(2026, 10, 13)
    assert daily.observation_count == 8


def test_date_filters_accept_optional_filters():
    filters = DateFilters(
        city="Manila",
        start_date="2026-10-01",
        end_date="2026-10-13",
    )

    assert filters.city == "Manila"
    assert filters.start_date == date(2026, 10, 1)
    assert filters.end_date == date(2026, 10, 13)

