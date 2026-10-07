import math
from datetime import datetime
from typing import Any

import requests

from common.logging import get_logger


logger = get_logger(__name__, "weather_validator.log")


class WeatherValidator:
    """
    Validate OpenWeather API configuration,
    geocoding data, and current weather data.
    """


    # api key validation
    @staticmethod
    def validate_openweathermap_api_key(api_key: str) -> bool:

        """Validate the OpenWeatherMap API key."""

        if not isinstance(api_key, str) or not api_key.strip():
            return False

        url = f"http://api.openweathermap.org/data/2.5/weather"

        params = {
            "q": "Manila",
            "appid": api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            return response.status_code == 200

        except requests.RequestException:
            return False
 
    # api key manager
    @staticmethod
    def validate_api_keys(openweather_api_key: str, _unused: str | None = None) -> bool:

        """Validate the configured OpenWeather API key."""

        return WeatherValidator.validate_openweathermap_api_key(openweather_api_key)


    # Geocoding and weather data validation
    @staticmethod
    def validate_openweather(openweather_data: dict) -> bool:

        """Validate the OpenWeather payload shape."""

        if not isinstance(openweather_data, dict):
            raise ValueError("OpenWeather data must be a dictionary.")


        # Required top-level sections in the OpenWeather payload
        required_sections = ["main", "wind", "weather", "coord"]

        missing_sections = [section for section in required_sections if section not in openweather_data]

        if missing_sections:
            raise ValueError(f"Missing sections in OpenWeather data: {missing_sections}")
        
        # Coordinate validation
        coord = openweather_data.get("coord", {})
        if not isinstance(coord, dict) or "lat" not in coord or "lon" not in coord:
            raise ValueError("OpenWeather data is missing required coordinate information.")

        latitude = coord.get("lat")
        longitude = coord.get("lon")

        if not WeatherValidator.validate_coordinates(latitude, longitude):
            raise ValueError("OpenWeather coordinates are out of valid range.")

        # main data validation
        main = openweather_data["main"]

        if not isinstance(main, dict):
            raise ValueError("OpenWeather 'main' section must be a dictionary.")

        main_required_fields = ["temp", "humidity", "pressure", "feels_like", "temp_min", "temp_max"]

        missing_main_fields = [field for field in main_required_fields if field not in main]

        if missing_main_fields:
            raise ValueError(f"OpenWeather 'main' section is missing required fields: {missing_main_fields}")


        # main weather values validation
        temperature = main.get("temp")
        feels_like = main.get("feels_like")
        temp_min = main.get("temp_min")
        temp_max = main.get("temp_max")
        pressure = main.get("pressure")
        humidity = main.get("humidity")

        numeric_values = {
            "temp": temperature,
            "feels_like": feels_like,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "pressure": pressure,
            "humidity": humidity,
        }

        for field, value in numeric_values.items():

            if not isinstance(
                value,
                (int, float),
            ):

                raise ValueError(
                    f"OpenWeather '{field}' "
                    "must be numeric."
                )

            if isinstance(value, float) and math.isnan(value):
                raise ValueError(
                    f"OpenWeather '{field}' "
                    "cannot be NaN."
                )

        # wind data validation
        wind = openweather_data["wind"]

        if not isinstance(wind, dict):
            raise ValueError("OpenWeather 'wind' section must be a dictionary.")

        wind_speed = wind.get("speed")
        if "speed" not in wind:
            raise ValueError("OpenWeather 'wind' section is missing required 'speed' field.")

        if not isinstance(wind_speed, (int, float)):
            raise ValueError("OpenWeather 'wind' speed must be a number.")

        if not (0 <= wind_speed <= 150):
            raise ValueError("OpenWeather 'wind' speed is out of valid range (0-150 m/s).")

        # weather data validation
        weather = openweather_data["weather"]

        if not isinstance(main, dict) or not isinstance(wind, dict) or not isinstance(weather, list):
            raise ValueError("OpenWeather data has an unexpected structure.")

        main_required_fields = ["temp", "humidity", "pressure", "feels_like", "temp_min", "temp_max"]

        missing_main_fields = [field for field in main_required_fields if field not in main]

        if missing_main_fields:
            raise ValueError(f"OpenWeather 'main' section is missing required fields: {missing_main_fields}")

        # Humidity, pressure, and temperature validation
        if not (0 <= humidity <= 100):
            raise ValueError("OpenWeather 'humidity' is out of valid range (0-100%).")
        if not (300 <= pressure <= 1100):
            raise ValueError("OpenWeather 'pressure' is out of valid range (300-1100 hPa).")

        # Observation timestamp validation
        observation_time = openweather_data.get("dt")
        if not isinstance(observation_time, int):
            raise ValueError("OpenWeather 'dt' must be an integer.")

        if observation_time < 0:
            raise ValueError("OpenWeather 'dt' cannot be negative.")

        # city name validation
        city_name = openweather_data.get("name")

        if city_name is None or not isinstance(city_name, str) or not city_name.strip():
            raise ValueError("OpenWeather 'name' (city name) is missing or invalid.")
        
        logger.info(f"OpenWeather data for {city_name} is valid.")
        
        return True



    @staticmethod
    def validate_geocoding(geocoding_data: dict) -> bool:

        """
        Validate the payload returned by OpenWeather Geocoding API.
        """

        if not isinstance(geocoding_data, dict):
            raise ValueError("Geocoding data must be a dictionary.")

        # Required fields in the geocoding payload
        required_fields = ["name", "lat", "lon"]

        missing = [field for field in required_fields if field not in geocoding_data]

        if missing:
            raise ValueError(f"Geocoding data is missing required fields: {missing}")

        # city name, latitude, and longitude validation
        latitude = geocoding_data.get("lat")
        if not isinstance(latitude, (int, float)):
            raise ValueError("Geocoding latitude must be a number.")

        longitude = geocoding_data.get("lon")
        if not isinstance(longitude, (int, float)):
            raise ValueError("Geocoding longitude must be a number.")

        city_name = geocoding_data.get("name")
        if not isinstance(city_name, str) or not city_name.strip():
            raise ValueError("Geocoding city name is missing or invalid.")

        if not WeatherValidator.validate_coordinates(latitude, longitude):
            raise ValueError("Geocoding coordinates are out of valid range.")

        country = geocoding_data.get("country")
        if country is not None and (not isinstance(country, str) or not country.strip()):
            raise ValueError("Geocoding country code is invalid.")
        logger.info(f"Geocoding data for {city_name} is valid.")


        return True



    @staticmethod
    def validate_city_coordinates(city: str, latitude: float, longitude: float) -> bool:

        """Validate the city coordinates using OpenWeather."""

        if not WeatherValidator.validate_city_name(city):
            return False
        if not WeatherValidator.validate_coordinates(latitude, longitude):
            return False

        url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid=YOUR_API_KEY"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return False
            data = response.json()
            return data.get("name", "").lower() == city.lower()
        except requests.RequestException:
            return False

 
    @staticmethod
    def validate_raw_json_record(record: dict[str, Any]) -> bool:
        """Validate a single saved raw JSON record created by save_json()."""

        if not isinstance(record, dict):
            raise ValueError("Saved JSON record must be a dictionary.")

        required_fields = [
            "city",
            "latitude",
            "longitude",
            "temperature",
            "pressure",
            "humidity",
            "observation_time",
            "source",
        ]

        missing = [field for field in required_fields if field not in record]
        if missing:
            raise ValueError(f"Saved JSON record is missing required fields: {missing}")

        city = record.get("city")
        if not WeatherValidator.validate_city_name(city):
            raise ValueError("Saved JSON city name is missing or invalid.")

        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if not WeatherValidator.validate_coordinates(latitude, longitude):
            raise ValueError("Saved JSON coordinates are out of valid range.")

        numeric_fields = {
            "temperature": record.get("temperature"),
            "pressure": record.get("pressure"),
            "humidity": record.get("humidity"),
            "wind_speed": record.get("wind_speed"),
        }

        for field_name, value in numeric_fields.items():
            if value is None:
                continue
            if not isinstance(value, (int, float)) or math.isnan(float(value)):
                raise ValueError(f"Saved JSON '{field_name}' must be numeric.")

        humidity = record.get("humidity")
        if humidity is not None and not (0 <= float(humidity) <= 100):
            raise ValueError("Saved JSON humidity is out of valid range (0-100%).")

        pressure = record.get("pressure")
        if pressure is not None and not (300 <= float(pressure) <= 1100):
            raise ValueError("Saved JSON pressure is out of valid range (300-1100 hPa).")

        if not isinstance(record.get("source"), str) or not record["source"].strip():
            raise ValueError("Saved JSON source is missing or invalid.")

        observation_time = record.get("observation_time")
        if observation_time is not None and not isinstance(observation_time, str):
            raise ValueError("Saved JSON observation_time must be a string timestamp.")

        dt_value = record.get("dt")
        if dt_value is not None and (not isinstance(dt_value, (int, float)) or float(dt_value) < 0):
            raise ValueError("Saved JSON dt must be a non-negative integer or float.")

        return True

    @staticmethod
    def validate_raw_json_data(data: dict[str, Any] | list[dict[str, Any]]) -> bool:
        """Validate a saved JSON payload, which can be a single record or a list of records."""

        if isinstance(data, list):
            for record in data:
                WeatherValidator.validate_raw_json_record(record)
            return True

        if isinstance(data, dict):
            return WeatherValidator.validate_raw_json_record(data)

        raise ValueError("Saved JSON data must be a dictionary or list of dictionaries.")

    @staticmethod
    def validate_saved_json_data(data: dict[str, Any] | list[dict[str, Any]]) -> bool:
        """Backward-compatible alias for saved raw JSON validation."""

        return WeatherValidator.validate_raw_json_data(data)

    @staticmethod
    def validate_saved_json_file(file_path: str | Any) -> bool:
        """Load a raw JSON file and validate its contents."""

        import json
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Saved JSON file does not exist: {path}")

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        return WeatherValidator.validate_raw_json_data(payload)

    @staticmethod
    def validate_weather_data_structure(data: dict) -> bool:

        """Validate the structure of the weather data."""

        if not isinstance(data, dict):
            return False

        for key, value in data.items():
            if not isinstance(key, str):
                return False
            if not isinstance(value, (int, float, str, dict, list)):
                return False

        return True



    @staticmethod
    def validate_weather_data_values(data: dict[str, Any]) -> bool:

        """Validate the values of the weather data."""

        if not isinstance(data, dict):
            return False
        for key in data:
            if key == "temp" and not isinstance(data[key], (int, float)):
                return False
            if key == "humidity" and not isinstance(data[key], (int, float)):
                return False
            if key == "pressure" and not isinstance(data[key], (int, float)):
                return False
        return True



    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:

        """Validate latitude and longitude ranges."""

        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return False
        
        if not math.isfinite(latitude) or not math.isfinite(longitude):
            return False
        if not (-90 <= latitude <= 90):
            return False
        if not (-180 <= longitude <= 180):
            return False
        return True



    @staticmethod
    def validate_city_name(city: str) -> bool:

        """Validate the city name."""

        return isinstance(city, str) and bool(city.strip())
 
    @staticmethod
    def validation_manager():

        """Return a dictionary of validation methods."""
 
        return {
            "validate_openweathermap_api_key": WeatherValidator.validate_openweathermap_api_key,
            "validate_api_keys": WeatherValidator.validate_api_keys,
            "validate_openweather": WeatherValidator.validate_openweather,
            "validate_geocoding": WeatherValidator.validate_geocoding,
            "validate_city_coordinates": WeatherValidator.validate_city_coordinates,
            "validate_raw_json_record": WeatherValidator.validate_raw_json_record,
            "validate_raw_json_data": WeatherValidator.validate_raw_json_data,
            "validate_saved_json_data": WeatherValidator.validate_saved_json_data,
            "validate_saved_json_file": WeatherValidator.validate_saved_json_file,
            "validate_weather_data_structure": WeatherValidator.validate_weather_data_structure,
            "validate_weather_data_values": WeatherValidator.validate_weather_data_values,
            "validate_coordinates": WeatherValidator.validate_coordinates,
            "validate_city_name": WeatherValidator.validate_city_name,
        }
