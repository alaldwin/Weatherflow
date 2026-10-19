
import httpx

from app.core.config import settings

BASE_URL = "https://api.openweathermap.org"


class OpenWeatherError(Exception):
    """Raised when an OpenWeather request fails."""


async def _get(path: str, params: dict) -> dict | list:
    api_key = settings.openweather_api_key

    if not api_key:
        raise OpenWeatherError("OpenWeather API key is not configured.")

    request_params = {**params, "appid": api_key}

    try:
        async with httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=15.0,
        ) as client:
            response = await client.get(path, params=request_params)
            response.raise_for_status()

            try:
                result = response.json()
            except (ValueError, UnicodeDecodeError) as exc:
                raise OpenWeatherError(
                    "OpenWeather returned an invalid JSON response."
                ) from exc

            if not isinstance(result, (dict, list)):
                raise OpenWeatherError(
                    "OpenWeather returned an unexpected response."
                )

            return result

    except httpx.HTTPStatusError as exc:
        raise OpenWeatherError(
            f"OpenWeather returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise OpenWeatherError(
            "Could not connect to OpenWeather."
        ) from exc


async def search_locations(
    query: str,
    limit: int = 5,
) -> list[dict]:
    result = await _get(
        "/geo/1.0/direct",
        {"q": query, "limit": limit},
    )

    if not isinstance(result, list):
        raise OpenWeatherError("Unexpected geocoding response.")

    if not all(isinstance(item, dict) for item in result):
        raise OpenWeatherError("Unexpected geocoding response.")

    return [
        {
            "name": item.get("name"),
            "state": item.get("state"),
            "country": item.get("country"),
            "lat": item.get("lat"),
            "lon": item.get("lon"),
        }
        for item in result
    ]


async def get_current_weather(
    lat: float,
    lon: float,
) -> dict:
    result = await _get(
        "/data/2.5/weather",
        {"lat": lat, "lon": lon, "units": "metric"},
    )

    if not isinstance(result, dict):
        raise OpenWeatherError("Unexpected weather response.")

    for key in ("sys", "coord", "main", "wind", "clouds"):
        if not isinstance(result.get(key), dict):
            raise OpenWeatherError("Unexpected weather response.")

    weather_items = result.get("weather")
    if (
        not isinstance(weather_items, list)
        or not weather_items
        or not isinstance(weather_items[0], dict)
    ):
        raise OpenWeatherError("Unexpected weather response.")

    return {
        "location": {
            "name": result.get("name"),
            "country": result["sys"].get("country"),
            "lat": result["coord"].get("lat"),
            "lon": result["coord"].get("lon"),
        },
        "temperature": result["main"].get("temp"),
        "feels_like": result["main"].get("feels_like"),
        "humidity": result["main"].get("humidity"),
        "pressure": result["main"].get("pressure"),
        "wind_speed": result["wind"].get("speed"),
        "wind_direction": result["wind"].get("deg"),
        "visibility": result.get("visibility"),
        "cloudiness": result["clouds"].get("all"),
        "weather": weather_items[0],
        "observation_time": result.get("dt"),
        "units": "metric",
        "source": "OpenWeather",
    }
