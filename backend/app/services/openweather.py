
import httpx

from app.core.config import settings

BASE_URL = "https://api.openweathermap.org"


class OpenWeatherError(Exception):
    """Raised when an OpenWeather request fails."""


async def _get(path: str, params: dict) -> dict | list:
    if not settings.openweather_api_key:
        raise OpenWeatherError("OpenWeather API key is not configured.")

    params["appid"] = settings.openweather_api_key

    try:
        async with httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=15.0,
        ) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()

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

    return {
        "location": {
            "name": result.get("name"),
            "country": result.get("sys", {}).get("country"),
            "lat": result.get("coord", {}).get("lat"),
            "lon": result.get("coord", {}).get("lon"),
        },
        "temperature": result.get("main", {}).get("temp"),
        "feels_like": result.get("main", {}).get("feels_like"),
        "humidity": result.get("main", {}).get("humidity"),
        "pressure": result.get("main", {}).get("pressure"),
        "wind_speed": result.get("wind", {}).get("speed"),
        "wind_direction": result.get("wind", {}).get("deg"),
        "visibility": result.get("visibility"),
        "cloudiness": result.get("clouds", {}).get("all"),
        "weather": result.get("weather", [{}])[0],
        "observation_time": result.get("dt"),
        "units": "metric",
        "source": "OpenWeather",
    }
