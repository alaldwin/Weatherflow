import importlib
import shutil
from pathlib import Path

from pipeline.ingestion.save_json import save_json
from pipeline.transformation.weather_transform import WeatherTransform
from pipeline.validation.weather_validator import WeatherValidator


def test_save_json_creates_unique_file_per_city():
    source = "openweather_test"
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "data" / "raw" / source
    shutil.rmtree(output_dir, ignore_errors=True)

    try:
        save_json({"dt": 1700000000, "temperature": 25}, "City One", source)
        save_json({"dt": 1700003600, "temperature": 30}, "City Two", source)

        saved_files = sorted(p.name for p in output_dir.iterdir())

        assert len(saved_files) == 2
        assert any("city_one" in name.lower() for name in saved_files)
        assert any("city_two" in name.lower() for name in saved_files)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_extract_functions_are_available_at_module_level():
    module = importlib.import_module("pipeline.ingestion.extract_api")

    assert callable(module.extract_openweather_data)
    assert callable(module.extract_weatherapi_data)


def test_validate_api_keys_uses_class_methods(monkeypatch):
    monkeypatch.setattr(
        WeatherValidator,
        "validate_openweathermap_api_key",
        staticmethod(lambda api_key: False),
    )
    monkeypatch.setattr(
        WeatherValidator,
        "validate_weatherapi_api_key",
        staticmethod(lambda api_key: True),
    )

    assert WeatherValidator.validate_api_keys("abc", "def") is False


def test_validate_coordinates_accepts_valid_range():
    assert WeatherValidator.validate_coordinates(14.5995, 120.9842) is True
    assert WeatherValidator.validate_coordinates(90, 180) is True
    assert WeatherValidator.validate_coordinates(91, 0) is False
    assert WeatherValidator.validate_coordinates(0, 181) is False


def test_transform_openweather_handles_single_payload_dict():
    payload = {
        "coord": {"lon": 120.9842, "lat": 14.5995},
        "weather": [{"description": "light rain"}],
        "main": {"temp": 32.21, "pressure": 1011, "humidity": 69},
        "wind": {"speed": 3.09},
        "name": "Manila",
    }

    df = WeatherTransform(payload, "openweather").transform()

    assert df.height == 1
    assert df["city"].to_list() == ["Manila"]
    assert df["temperature"].to_list() == [32.21]


def test_transform_weatherapi_handles_single_payload_dict():
    payload = {
        "location": {"name": "Manila", "lat": 14.5995, "lon": 120.9842},
        "current": {
            "temp_c": 31.5,
            "humidity": 65,
            "pressure_mb": 1011,
            "wind_kph": 6.2,
            "condition": {"text": "Partly cloudy"},
        },
    }

    df = WeatherTransform(payload, "weatherapi").transform()

    assert df.height == 1
    assert df["city"].to_list() == ["Manila"]
    assert df["temperature"].to_list() == [31.5]
