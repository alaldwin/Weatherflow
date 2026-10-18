from datetime import date, datetime

import pytest
from app.schemas.weather import (
    CityComparison,
    CurrentWeather,
    DailyWeather,
    DateFilters,
    SortOptions,
)
from pydantic import ValidationError


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



def test_sort_options_accept_valid_values():
    options = SortOptions(sort_by="temperature", order="desc")

    assert options.sort_by == "temperature"
    assert options.order == "desc"


@pytest.mark.parametrize(
    "sort_by",
    ["temperature", "humidity", "wind_speed", "city"],
)
def test_sort_options_accept_supported_sort_fields(sort_by):
    options = SortOptions(sort_by=sort_by, order="asc")

    assert options.sort_by == sort_by


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_sort_options_accept_supported_orders(order):
    options = SortOptions(sort_by="temperature", order=order)

    assert options.order == order


def test_sort_options_reject_invalid_values():
    with pytest.raises(ValidationError):
        SortOptions(sort_by="unknown_field", order="desc")

    with pytest.raises(ValidationError):
        SortOptions(sort_by="temperature", order="sideways")



def test_date_filters_reject_start_date_after_end_date():
    with pytest.raises(ValidationError):
        DateFilters(
            start_date="2026-10-14",
            end_date="2026-10-13",
        )


def test_date_filters_accept_same_start_and_end_date():
    filters = DateFilters(
        start_date="2026-10-13",
        end_date="2026-10-13",
    )

    assert filters.start_date == date(2026, 10, 13)
    assert filters.end_date == date(2026, 10, 13)



@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", 91),
        ("latitude", -91),
        ("longitude", 181),
        ("longitude", -181),
        ("humidity", 101),
        ("humidity", -1),
        ("cloudiness", 101),
        ("cloudiness", -1),
    ],
)


def test_current_weather_rejects_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        CurrentWeather(city="Manila", **{field: value})


@pytest.mark.parametrize("field", ["humidity", "cloudiness"])
def test_city_comparison_rejects_out_of_range_percentages(field):
    with pytest.raises(ValidationError):
        CityComparison(city="Manila", **{field: 101})
