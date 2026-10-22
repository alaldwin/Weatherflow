import json
import os

import requests
from dotenv import load_dotenv

from common.logging import get_logger


class WeatherAPIUnavailable(Exception):
    """Raised when the weather API is temporarily unreachable."""

load_dotenv()

logger = get_logger(__name__, "extract_api.log")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
 

def extract_openweather_data(latitude, longitude, city=None):
    """Extract current weather data from the OpenWeatherMap API."""

    api_key = OPENWEATHER_API_KEY or os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        logger.error("OPENWEATHER_API_KEY is not configured.")
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": api_key,
        "units": "metric",
    }

    try:
        response = requests.get(url, params=params, timeout=(5, 10))

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            logger.error("OpenWeather returned an unexpected response format.")
            return None

        if city:
            data["city"] = city

        logger.info(
            "Successfully extracted weather data for %s.",
            city or data.get("name", "unknown city"),
        )
        return data

    except requests.exceptions.Timeout as exc:
        logger.warning("OpenWeather API timed out: %s", exc)
        raise WeatherAPIUnavailable("OpenWeather API timed out") from exc

    except requests.exceptions.ConnectionError as exc:
        logger.warning("OpenWeather API connection failed: %s", exc)
        raise WeatherAPIUnavailable(
            "OpenWeather API is unreachable"
        ) from exc

    except requests.exceptions.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        if status_code in (408, 429) or (
            status_code is not None and status_code >= 500
        ):
            logger.warning(
                "Temporary OpenWeather API HTTP error: %s",
                status_code,
            )
            raise WeatherAPIUnavailable(
                f"Temporary OpenWeather API HTTP error: {status_code}"
            ) from exc

        logger.error("Non-retryable OpenWeather API HTTP error: %s", exc)
        return None

    except requests.exceptions.RequestException as exc:
        logger.error("OpenWeather request failed: %s", exc)
        return None

    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Invalid OpenWeather response: %s", exc)
        return None



def extract_geocoding_data(latitude, longitude, city=None):
    """Extract geographic metadata for a city using the OpenWeather geocoding API."""

    api_key = OPENWEATHER_API_KEY or os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        logger.error("OPENWEATHER_API_KEY is not configured.")
        return None

    url = "http://api.openweathermap.org/geo/1.0/direct"
    
    params = {"limit": 1, "appid": api_key}

    if city:
        params["q"] = city
    else:
        params["lat"] = latitude
        params["lon"] = longitude


    try:

        response = requests.get(url, params=params, timeout=10)

        response.raise_for_status()

        data = response.json()
        if not data:
            logger.warning(f"No geocoding data found for city: {city}")

            return None

        logger.info("Successfully extracted geocoding data from OpenWeather API.")

        return data[0]

    except requests.exceptions.Timeout as exc:
        logger.warning("Geocoding API timed out: %s", exc)
        raise WeatherAPIUnavailable("Geocoding API timed out") from exc

    except requests.exceptions.ConnectionError as exc:
        logger.warning("Geocoding API connection failed: %s", exc)
        raise WeatherAPIUnavailable(
            "Geocoding API is unreachable"
        ) from exc

    except requests.exceptions.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        if status_code in (408, 429) or (
            status_code is not None and status_code >= 500
        ):
            logger.warning(
                "Temporary geocoding API HTTP error: %s",
                status_code,
            )
            raise WeatherAPIUnavailable(
                f"Temporary geocoding API HTTP error: {status_code}"
            ) from exc

        logger.error("Non-retryable geocoding HTTP error: %s", exc)
        return None

