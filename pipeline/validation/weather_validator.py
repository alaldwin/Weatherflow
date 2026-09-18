import requests

from common.logging import get_logger

logger = get_logger(__name__, "weather_validator.log")


class WeatherValidator:

    """Validate weather-related data and API keys."""


    @staticmethod
    def validate_openweathermap_api_key(api_key: str) -> bool:

        """Validate the OpenWeatherMap API key."""

        if not isinstance(api_key, str) or not api_key.strip():
            return False

        url = f"http://api.openweathermap.org/data/2.5/weather?q=London&appid={api_key}"
        try:
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False



    @staticmethod
    def validate_weatherapi_api_key(api_key: str) -> bool:

        """Validate the WeatherAPI API key."""

        if not isinstance(api_key, str) or not api_key.strip():
            return False

        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q=London"
        try:
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False



    @staticmethod
    def validate_api_keys(openweather_api_key: str, weatherapi_api_key: str) -> bool:

        """Validate both API keys."""

        is_openweather_valid = WeatherValidator.validate_openweathermap_api_key(openweather_api_key)
        is_weatherapi_valid = WeatherValidator.validate_weatherapi_api_key(weatherapi_api_key)
        return is_openweather_valid and is_weatherapi_valid



    @staticmethod
    def validate_openweather(openweather_data: dict) -> bool:

        """Validate the OpenWeather payload shape."""

        if not isinstance(openweather_data, dict):
            raise ValueError("OpenWeather data must be a dictionary.")

        required_sections = ["main", "wind", "weather"]
        missing_sections = [section for section in required_sections if section not in openweather_data]
        if missing_sections:
            raise ValueError(f"Missing sections in OpenWeather data: {missing_sections}")

        main = openweather_data["main"]
        wind = openweather_data["wind"]
        weather = openweather_data["weather"]

        if not isinstance(main, dict) or not isinstance(wind, dict) or not isinstance(weather, list):
            raise ValueError("OpenWeather data has an unexpected structure.")

        temperature = main.get("temp")
        humidity = main.get("humidity")
        pressure = main.get("pressure")
        wind_speed = wind.get("speed")
        weather_description = weather[0].get("description") if weather else None

        if any(value is None for value in (temperature, humidity, pressure, wind_speed, weather_description)):
            raise ValueError("OpenWeather data is missing required values.")

        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be a number.")
        if not isinstance(humidity, (int, float)):
            raise ValueError("Humidity must be a number.")

        return True



    @staticmethod
    def validate_weatherapi(weatherapi_data: dict) -> bool:

        """Validate the WeatherAPI payload shape."""

        if not isinstance(weatherapi_data, dict):
            raise ValueError("WeatherAPI data must be a dictionary.")

        if "current" not in weatherapi_data:
            raise ValueError("WeatherAPI data is missing the current section.")

        current = weatherapi_data["current"]
        if not isinstance(current, dict):
            raise ValueError("WeatherAPI current section must be a dictionary.")

        temperature = current.get("temp_c")
        humidity = current.get("humidity")
        pressure = current.get("pressure_mb")
        wind_speed = current.get("wind_kph")
        weather_description = current.get("condition", {}).get("text")

        if any(value is None for value in (temperature, humidity, pressure, wind_speed, weather_description)):
            raise ValueError("WeatherAPI data is missing required values.")

        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be a number.")
        if not isinstance(humidity, (int, float)):
            raise ValueError("Humidity must be a number.")

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
    def validate_city_coordinates_weatherapi(city: str, latitude: float, longitude: float, api_key: str) -> bool:

        """Validate the city coordinates using WeatherAPI."""

        if not WeatherValidator.validate_city_name(city):
            return False
        if not WeatherValidator.validate_coordinates(latitude, longitude):
            return False

        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={latitude},{longitude}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return False
            data = response.json()
            return data.get("location", {}).get("name", "").lower() == city.lower()
        except requests.RequestException:
            return False



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
    def validate_weather_data_values(data: dict) -> bool:

        """Validate the values of the weather data."""

        if "temperature" in data and not (-100 <= data["temperature"] <= 100):
            return False
        if "humidity" in data and not (0 <= data["humidity"] <= 100):
            return False
        if "pressure" in data and not (300 <= data["pressure"] <= 1100):
            return False
        if "wind_speed" in data and not (0 <= data["wind_speed"] <= 150):
            return False

        return True



    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:

        """Validate latitude and longitude ranges."""

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
            "validate_weatherapi_api_key": WeatherValidator.validate_weatherapi_api_key,
            "validate_api_keys": WeatherValidator.validate_api_keys,
            "validate_openweather": WeatherValidator.validate_openweather,
            "validate_weatherapi": WeatherValidator.validate_weatherapi,
            "validate_city_coordinates": WeatherValidator.validate_city_coordinates,
            "validate_city_coordinates_weatherapi": WeatherValidator.validate_city_coordinates_weatherapi,
            "validate_weather_data_structure": WeatherValidator.validate_weather_data_structure,
            "validate_weather_data_values": WeatherValidator.validate_weather_data_values,
            "validate_coordinates": WeatherValidator.validate_coordinates,
            "validate_city_name": WeatherValidator.validate_city_name,
        }
