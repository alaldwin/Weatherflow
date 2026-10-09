import json
import os

import requests
from dotenv import load_dotenv

from common.logging import get_logger

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
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info("Successfully extracted data from OpenWeather API.")
        return data
    except requests.exceptions.Timeout as exc:
        logger.error(f"Timeout error extracting data from OpenWeather API: {exc}")
        return None
    except requests.exceptions.HTTPError as exc:
        logger.error(f"HTTP error extracting data from OpenWeather API: {exc}")
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.error(f"Connection error extracting data from OpenWeather API: {exc}")
        return None
    except requests.exceptions.RequestException as exc:
        logger.error(f"Error extracting data from OpenWeather API: {exc}")
        return None
    except json.JSONDecodeError as exc:
        logger.error(f"JSON decode error extracting data from OpenWeather API: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Unexpected error extracting data from OpenWeather API: {exc}")
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
        logger.error(f"Timeout error extracting geocoding data: {exc}")
        return None
    except requests.exceptions.HTTPError as exc:
        logger.error(f"HTTP error extracting geocoding data: {exc}")
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.error(f"Connection error extracting geocoding data: {exc}")
        return None
    except requests.exceptions.RequestException as exc:
        logger.error(f"Error extracting geocoding data: {exc}")
        return None
    except json.JSONDecodeError as exc:
        logger.error(f"JSON decode error extracting geocoding data: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Unexpected error extracting geocoding data: {exc}")
        return None