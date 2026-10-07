
import math

import pytest
import requests

from pipeline.validation.weather_validator import WeatherValidator


# ============================================================
# Test Data
# ============================================================

@pytest.fixture
def valid_openweather_data():
    """Valid OpenWeather Current Weather API response."""

    return {
        "coord": {
            "lon": 120.9842,
            "lat": 14.5995,
        },
        "weather": [
            {
                "id": 800,
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d",
            }
        ],
        "main": {
            "temp": 30.5,
            "feels_like": 33.0,
            "temp_min": 29.5,
            "temp_max": 31.5,
            "pressure": 1012,
            "humidity": 70,
        },
        "wind": {
            "speed": 4.5,
            "deg": 120,
        },
        "dt": 1791283200,
        "name": "Manila",
    }


@pytest.fixture
def valid_geocoding_data():
    """Valid OpenWeather Geocoding API response."""

    return {
        "name": "Manila",
        "lat": 14.5995,
        "lon": 120.9842,
        "country": "PH",
        "state": "Metro Manila",
    }


@pytest.fixture
def valid_raw_json_record():
    """Valid transformed raw JSON record."""

    return {
        "city": "Manila",
        "latitude": 14.5995,
        "longitude": 120.9842,
        "temperature": 30.5,
        "pressure": 1012,
        "humidity": 70,
        "wind_speed": 4.5,
        "observation_time": "2026-10-06T10:00:00+00:00",
        "source": "openweather",
        "dt": 1791283200,
    }


# ============================================================
# OpenWeather Validation
# ============================================================

def test_validate_openweather_valid_data(valid_openweather_data):
    """Valid OpenWeather data should pass."""

    result = WeatherValidator.validate_openweather(
        valid_openweather_data
    )

    assert result is True


def test_validate_openweather_rejects_non_dictionary():
    """OpenWeather data must be a dictionary."""

    with pytest.raises(ValueError, match="must be a dictionary"):
        WeatherValidator.validate_openweather(
            "invalid data"
        )


def test_validate_openweather_missing_required_section(
    valid_openweather_data,
):
    """Missing top-level sections should fail."""

    del valid_openweather_data["main"]

    with pytest.raises(
        ValueError,
        match="Missing sections",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_missing_coordinate(
    valid_openweather_data,
):
    """Missing coordinates should fail."""

    del valid_openweather_data["coord"]["lat"]

    with pytest.raises(
        ValueError,
        match="coordinate",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_invalid_temperature(
    valid_openweather_data,
):
    """Temperature must be numeric."""

    valid_openweather_data["main"]["temp"] = "30.5"

    with pytest.raises(
        ValueError,
        match="temp.*must be numeric",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_nan_temperature(
    valid_openweather_data,
):
    """Temperature cannot be NaN."""

    valid_openweather_data["main"]["temp"] = math.nan

    with pytest.raises(
        ValueError,
        match="cannot be NaN",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_invalid_humidity(
    valid_openweather_data,
):
    """Humidity must be between 0 and 100."""

    valid_openweather_data["main"]["humidity"] = 150

    with pytest.raises(
        ValueError,
        match="humidity",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_invalid_pressure(
    valid_openweather_data,
):
    """Pressure must be between 300 and 1100 hPa."""

    valid_openweather_data["main"]["pressure"] = 2000

    with pytest.raises(
        ValueError,
        match="pressure",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_invalid_wind_speed(
    valid_openweather_data,
):
    """Wind speed must be between 0 and 150 m/s."""

    valid_openweather_data["wind"]["speed"] = 200

    with pytest.raises(
        ValueError,
        match="wind.*out of valid range",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_negative_wind_speed(
    valid_openweather_data,
):
    """Wind speed cannot be negative."""

    valid_openweather_data["wind"]["speed"] = -1

    with pytest.raises(
        ValueError,
        match="wind.*out of valid range",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_invalid_timestamp(
    valid_openweather_data,
):
    """OpenWeather dt must be an integer."""

    valid_openweather_data["dt"] = "1791283200"

    with pytest.raises(
        ValueError,
        match="dt.*integer",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_negative_timestamp(
    valid_openweather_data,
):
    """OpenWeather dt cannot be negative."""

    valid_openweather_data["dt"] = -1

    with pytest.raises(
        ValueError,
        match="dt.*negative",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


def test_validate_openweather_missing_city_name(
    valid_openweather_data,
):
    """City name is required."""

    valid_openweather_data["name"] = ""

    with pytest.raises(
        ValueError,
        match="city name",
    ):
        WeatherValidator.validate_openweather(
            valid_openweather_data
        )


# ============================================================
# Geocoding Validation
# ============================================================

def test_validate_geocoding_valid_data(valid_geocoding_data):
    """Valid geocoding data should pass."""

    result = WeatherValidator.validate_geocoding(
        valid_geocoding_data
    )

    assert result is True


def test_validate_geocoding_rejects_non_dictionary():
    """Geocoding data must be a dictionary."""

    with pytest.raises(
        ValueError,
        match="must be a dictionary",
    ):
        WeatherValidator.validate_geocoding(
            []
        )


def test_validate_geocoding_missing_required_field(
    valid_geocoding_data,
):
    """Required geocoding fields must exist."""

    del valid_geocoding_data["lat"]

    with pytest.raises(
        ValueError,
        match="missing required fields",
    ):
        WeatherValidator.validate_geocoding(
            valid_geocoding_data
        )


def test_validate_geocoding_invalid_latitude(
    valid_geocoding_data,
):
    """Latitude must be numeric."""

    valid_geocoding_data["lat"] = "14.5995"

    with pytest.raises(
        ValueError,
        match="latitude must be a number",
    ):
        WeatherValidator.validate_geocoding(
            valid_geocoding_data
        )


def test_validate_geocoding_invalid_longitude(
    valid_geocoding_data,
):
    """Longitude must be numeric."""

    valid_geocoding_data["lon"] = "120.9842"

    with pytest.raises(
        ValueError,
        match="longitude must be a number",
    ):
        WeatherValidator.validate_geocoding(
            valid_geocoding_data
        )


def test_validate_geocoding_invalid_coordinates(
    valid_geocoding_data,
):
    """Coordinates must be within valid geographic ranges."""

    valid_geocoding_data["lat"] = 100

    with pytest.raises(
        ValueError,
        match="out of valid range",
    ):
        WeatherValidator.validate_geocoding(
            valid_geocoding_data
        )


def test_validate_geocoding_invalid_city_name(
    valid_geocoding_data,
):
    """City name cannot be empty."""

    valid_geocoding_data["name"] = ""

    with pytest.raises(
        ValueError,
        match="city name",
    ):
        WeatherValidator.validate_geocoding(
            valid_geocoding_data
        )


def test_validate_geocoding_invalid_country(
    valid_geocoding_data,
):
    """Country must be a non-empty string when provided."""

    valid_geocoding_data["country"] = 123

    with pytest.raises(
        ValueError,
        match="country code",
    ):
        WeatherValidator.validate_geocoding(
            valid_geocoding_data
        )


# ============================================================
# Coordinate Validation
# ============================================================

@pytest.mark.parametrize(
    "latitude, longitude",
    [
        (0, 0),
        (14.5995, 120.9842),
        (90, 180),
        (-90, -180),
    ],
)
def test_validate_coordinates_valid(
    latitude,
    longitude,
):
    """Valid coordinates should return True."""

    assert (
        WeatherValidator.validate_coordinates(
            latitude,
            longitude,
        )
        is True
    )


@pytest.mark.parametrize(
    "latitude, longitude",
    [
        (91, 120),
        (-91, 120),
        (14, 181),
        (14, -181),
        ("14.5", 120),
        (14, "120.9"),
        (math.nan, 120),
        (14, math.inf),
    ],
)
def test_validate_coordinates_invalid(
    latitude,
    longitude,
):
    """Invalid coordinates should return False."""

    assert (
        WeatherValidator.validate_coordinates(
            latitude,
            longitude,
        )
        is False
    )


# ============================================================
# City Name Validation
# ============================================================

@pytest.mark.parametrize(
    "city",
    [
        "Manila",
        "Quezon City",
        "Cebu City",
        "Davao City",
        "Baguio",
    ],
)
def test_validate_city_name_valid(city):
    """Valid city names should return True."""

    assert WeatherValidator.validate_city_name(city) is True


@pytest.mark.parametrize(
    "city",
    [
        "",
        "   ",
        None,
        123,
    ],
)
def test_validate_city_name_invalid(city):
    """Invalid city names should return False."""

    assert WeatherValidator.validate_city_name(city) is False


# ============================================================
# Raw JSON Validation
# ============================================================

def test_validate_raw_json_record_valid(
    valid_raw_json_record,
):
    """Valid saved JSON record should pass."""

    result = WeatherValidator.validate_raw_json_record(
        valid_raw_json_record
    )

    assert result is True


def test_validate_raw_json_record_missing_field(
    valid_raw_json_record,
):
    """Missing required raw JSON fields should fail."""

    del valid_raw_json_record["city"]

    with pytest.raises(
        ValueError,
        match="missing required fields",
    ):
        WeatherValidator.validate_raw_json_record(
            valid_raw_json_record
        )


def test_validate_raw_json_record_invalid_temperature(
    valid_raw_json_record,
):
    """Temperature must be numeric."""

    valid_raw_json_record["temperature"] = "30.5"

    with pytest.raises(
        ValueError,
        match="temperature.*numeric",
    ):
        WeatherValidator.validate_raw_json_record(
            valid_raw_json_record
        )


def test_validate_raw_json_record_invalid_humidity(
    valid_raw_json_record,
):
    """Humidity must be between 0 and 100."""

    valid_raw_json_record["humidity"] = 150

    with pytest.raises(
        ValueError,
        match="humidity",
    ):
        WeatherValidator.validate_raw_json_record(
            valid_raw_json_record
        )


def test_validate_raw_json_record_invalid_pressure(
    valid_raw_json_record,
):
    """Pressure must be within the expected range."""

    valid_raw_json_record["pressure"] = 2000

    with pytest.raises(
        ValueError,
        match="pressure",
    ):
        WeatherValidator.validate_raw_json_record(
            valid_raw_json_record
        )


def test_validate_raw_json_data_single_record(
    valid_raw_json_record,
):
    """A single dictionary should be accepted."""

    assert (
        WeatherValidator.validate_raw_json_data(
            valid_raw_json_record
        )
        is True
    )


def test_validate_raw_json_data_multiple_records(
    valid_raw_json_record,
):
    """A list of valid records should be accepted."""

    second_record = valid_raw_json_record.copy()

    second_record["observation_time"] = (
        "2026-10-06T11:00:00+00:00"
    )

    second_record["dt"] = 1791286800

    data = [
        valid_raw_json_record,
        second_record,
    ]

    assert (
        WeatherValidator.validate_raw_json_data(
            data
        )
        is True
    )


def test_validate_raw_json_data_invalid_type():
    """Raw JSON data must be a dictionary or list."""

    with pytest.raises(
        ValueError,
        match="dictionary or list",
    ):
        WeatherValidator.validate_raw_json_data(
            "invalid"
        )


# ============================================================
# Weather Structure Validation
# ============================================================

def test_validate_weather_data_structure_valid():
    """Basic weather data structure should pass."""

    data = {
        "temp": 30.5,
        "humidity": 70,
        "city": "Manila",
        "main": {
            "pressure": 1012,
        },
        "weather": [],
    }

    assert (
        WeatherValidator.validate_weather_data_structure(
            data
        )
        is True
    )


def test_validate_weather_data_structure_invalid():
    """Non-dictionary weather data should fail."""

    assert (
        WeatherValidator.validate_weather_data_structure(
            "invalid"
        )
        is False
    )


# ============================================================
# Weather Value Validation
# ============================================================

def test_validate_weather_data_values_valid():
    """Valid weather values should pass."""

    data = {
        "temp": 30.5,
        "humidity": 70,
        "pressure": 1012,
    }

    assert (
        WeatherValidator.validate_weather_data_values(
            data
        )
        is True
    )


def test_validate_weather_data_values_invalid_temperature():
    """Temperature must be numeric."""

    data = {
        "temp": "30.5",
    }

    assert (
        WeatherValidator.validate_weather_data_values(
            data
        )
        is False
    )


def test_validate_weather_data_values_invalid_humidity():
    """Humidity must be numeric."""

    data = {
        "humidity": "70",
    }

    assert (
        WeatherValidator.validate_weather_data_values(
            data
        )
        is False
    )


# ============================================================
# API Key Validation
# ============================================================

def test_validate_openweathermap_api_key_valid(
    monkeypatch,
):
    """
    A successful HTTP response should validate the API key.
    No real API request is made.
    """

    class MockResponse:
        status_code = 200

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(
        requests,
        "get",
        mock_get,
    )

    result = (
        WeatherValidator
        .validate_openweathermap_api_key(
            "fake-valid-api-key"
        )
    )

    assert result is True


def test_validate_openweathermap_api_key_invalid_empty():
    """Empty API keys should fail without an HTTP request."""

    assert (
        WeatherValidator
        .validate_openweathermap_api_key("")
        is False
    )


def test_validate_openweathermap_api_key_invalid_whitespace():
    """Whitespace-only API keys should fail."""

    assert (
        WeatherValidator
        .validate_openweathermap_api_key("   ")
        is False
    )


def test_validate_openweathermap_api_key_request_error(
    monkeypatch,
):
    """HTTP request errors should return False."""

    def mock_get(*args, **kwargs):
        raise requests.RequestException(
            "Connection failed"
        )

    monkeypatch.setattr(
        requests,
        "get",
        mock_get,
    )

    result = (
        WeatherValidator
        .validate_openweathermap_api_key(
            "fake-api-key"
        )
    )

    assert result is False


# ============================================================
# Validation Manager
# ============================================================

def test_validation_manager():
    """Validation manager should expose all validation methods."""

    manager = WeatherValidator.validation_manager()

    assert isinstance(manager, dict)

    expected_methods = [
        "validate_openweathermap_api_key",
        "validate_api_keys",
        "validate_openweather",
        "validate_geocoding",
        "validate_city_coordinates",
        "validate_raw_json_record",
        "validate_raw_json_data",
        "validate_saved_json_data",
        "validate_saved_json_file",
        "validate_weather_data_structure",
        "validate_weather_data_values",
        "validate_coordinates",
        "validate_city_name",
    ]

    for method_name in expected_methods:
        assert method_name in manager
        assert callable(manager[method_name])
