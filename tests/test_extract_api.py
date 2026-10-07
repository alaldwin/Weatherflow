import importlib

from pipeline.validation.weather_validator import WeatherValidator


def test_extract_functions_are_available_at_module_level():
    module = importlib.import_module("pipeline.ingestion.extract_api")

    assert callable(module.extract_openweather_data)
    assert callable(module.extract_geocoding_data)


def test_extract_geocoding_uses_geocoding_url_and_key(monkeypatch):
    module = importlib.import_module("pipeline.ingestion.extract_api")

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return FakeResponse([{"name": "Manila", "lat": 14.5995, "lon": 120.9842, "country": "PH"}])

    monkeypatch.setattr(module, "OPENWEATHER_API_KEY", "openweather-test-key")
    monkeypatch.setattr(module.requests, "get", fake_get)

    data = module.extract_geocoding_data(14.5995, 120.9842, "Manila")

    assert data["name"] == "Manila"
    assert data["lat"] == 14.5995
    assert captured["url"] == "http://api.openweathermap.org/geo/1.0/direct"
    assert captured["params"]["q"] == "Manila"
    assert captured["params"]["limit"] == 1


def test_incremental_state_uses_project_root_path():
    module = importlib.import_module("pipeline.ingestion.incremetal_api")

    assert module.STATE_FILE.is_absolute()
    assert module.STATE_FILE.parts[-3:] == ("weatherflow", "data", "state") or "state" in module.STATE_FILE.parts[-2:]


def test_validate_api_keys_uses_class_methods(monkeypatch):
    monkeypatch.setattr(
        WeatherValidator,
        "validate_openweathermap_api_key",
        staticmethod(lambda api_key: False),
    )

    assert WeatherValidator.validate_api_keys("abc") is False


def test_validate_coordinates_accepts_valid_range():
    assert WeatherValidator.validate_coordinates(14.5995, 120.9842) is True
    assert WeatherValidator.validate_coordinates(90, 180) is True
    assert WeatherValidator.validate_coordinates(91, 0) is False
    assert WeatherValidator.validate_coordinates(0, 181) is False


def test_validate_raw_json_data_accepts_saved_weather_record():
    payload = [{
        "city": "Manila",
        "latitude": 14.5995,
        "longitude": 120.9842,
        "temperature": 30.5,
        "feels_like": 29.8,
        "temp_min": 28.0,
        "temp_max": 32.0,
        "pressure": 1011,
        "humidity": 70,
        "visibility": 10000,
        "wind_speed": 3.1,
        "wind_direction": 150,
        "cloudiness": 20,
        "weather_id": 800,
        "weather_main": "Clear",
        "weather_description": "clear sky",
        "dt": 1700000000,
        "observation_time": "2024-11-14T00:00:00+00:00",
        "source": "openweather",
        "ingested_time": "2024-11-14T00:00:00+00:00",
    }]

    assert WeatherValidator.validate_raw_json_data(payload) is True


def test_transform_raw_json_record_to_dataframe():
    from pipeline.transformation.weather_transform import WeatherTransform

    payload = [{
        "city": "Manila",
        "latitude": 14.5995,
        "longitude": 120.9842,
        "temperature": 30.5,
        "pressure": 1011,
        "humidity": 70,
        "weather_description": "clear sky",
        "wind_speed": 3.1,
        "source": "openweather",
    }]

    df = WeatherTransform(payload, "openweather").transform()

    assert df.height == 1
    assert df["city"].to_list() == ["Manila"]
    assert df["temperature"].to_list() == [30.5]
    assert df["weather_description"].to_list() == ["clear sky"]
