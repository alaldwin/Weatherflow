import json
import os

import requests

from dotenv import load_dotenv

from common.logging import get_logger

load_dotenv()

logger = get_logger(__name__, "extract_api.log")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")


def extract_openweather_data(LATITUDE, LONGITUDE, CITY):

    """Extract weather data from the OpenWeather API."""

    if not OPENWEATHER_API_KEY:
        logger.error("OPENWEATHER_API_KEY is not configured.")
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "lat": LATITUDE,
        "lon": LONGITUDE,
        "q": CITY,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.info("Successfully extracted data from OpenWeather API.")

        return data

    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error extracting data from OpenWeather API: {e}")
        return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error extracting data from OpenWeather API: {e}")
        return None

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error extracting data from OpenWeather API: {e}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error extracting data from OpenWeather API: {e}")
        return None

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error extracting data from OpenWeather API: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error extracting data from OpenWeather API: {e}")
        return None



def extract_weatherapi_data(LATITUDE, LONGITUDE, CITY):

    """Extract weather data from the WeatherAPI."""

    if not WEATHERAPI_API_KEY:
        logger.error("WEATHERAPI_API_KEY is not configured.")
        return None

    url = "https://api.weatherapi.com/v1/current.json"

    params = {
        "key": WEATHERAPI_API_KEY,
        "q": f"{LATITUDE},{LONGITUDE}",
        "aqi": "no",
    }

    try:

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        logger.info("Successfully extracted data from WeatherAPI.")

        return data

    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error extracting data from WeatherAPI: {e}")
        return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error extracting data from WeatherAPI: {e}")
        return None

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error extracting data from WeatherAPI: {e}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error extracting data from WeatherAPI: {e}")
        return None

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error extracting data from WeatherAPI: {e}")
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error extracting data from WeatherAPI: {e}")
        return None