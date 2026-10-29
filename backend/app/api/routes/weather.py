
import logging
from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine
from app.services.openweather import (
    OpenWeatherError,
    get_current_weather,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)

MAX_DISTANCE_KM = 30

DATABASE_WEATHER_QUERY = text("""
    SELECT
        city,
        country,
        latitude,
        longitude,
        temperature,
        feels_like,
        humidity,
        pressure,
        visibility,
        wind_speed,
        wind_direction,
        cloudiness,
        weather_main,
        weather_description,
        weather_icon,
        observation_time,
        sunrise,
        sunset
    FROM mrt_dev.mrt_current_weather
    WHERE latitude IS NOT NULL
      AND longitude IS NOT NULL
      AND temperature IS NOT NULL
""")


def distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate the distance between two coordinates."""
    lat1, lon1, lat2, lon2 = map(
        radians, (lat1, lon1, lat2, lon2)
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 6371 * 2 * asin(sqrt(min(1.0, a)))


def database_weather_fallback(lat: float, lon: float):
    """Return the nearest database observation within 30 km."""
    with engine.connect() as connection:
        rows = connection.execute(
            DATABASE_WEATHER_QUERY
        ).mappings().all()

    if not rows:
        return None

    nearest = min(
        rows,
        key=lambda row: distance_km(
            lat,
            lon,
            row["latitude"],
            row["longitude"],
        ),
    )

    distance = distance_km(
        lat,
        lon,
        nearest["latitude"],
        nearest["longitude"],
    )

    if distance > MAX_DISTANCE_KM:
        return None

    observed_at = nearest["observation_time"]
    observation_timestamp = (
        int(observed_at.timestamp())
        if observed_at is not None
        else None
    )

    return {
        "location": {
            "name": nearest["city"],
            "country": nearest["country"],
            "lat": nearest["latitude"],
            "lon": nearest["longitude"],
        },
        "temperature": nearest["temperature"],
        "feels_like": nearest["feels_like"],
        "humidity": nearest["humidity"],
        "pressure": nearest["pressure"],
        "wind_speed": nearest["wind_speed"],
        "wind_direction": nearest["wind_direction"],
        "visibility": nearest["visibility"],
        "cloudiness": nearest["cloudiness"],
        "weather": {
            "main": nearest["weather_main"],
            "description": nearest["weather_description"],
            "icon": nearest["weather_icon"],
        },
        "observation_time": observation_timestamp,
        "sunrise": nearest["sunrise"],
        "sunset": nearest["sunset"],
        "units": "metric",
        "source": "Weatherflow PostgreSQL (offline fallback)",
    }


@router.get("/coordinates/current")
async def current_weather(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180), 
): 
    try:
        return await get_current_weather(lat, lon)

    except OpenWeatherError as exc:
        logger.warning(
            "OpenWeather unavailable for coordinates %.4f, %.4f; "
            "trying PostgreSQL fallback: %s",
            lat,
            lon,
            exc,
        )

    try:
        cached_weather = database_weather_fallback(lat, lon)
    except SQLAlchemyError:
        logger.exception("Database weather fallback failed")
        raise HTTPException(
            status_code=503,
            detail="OpenWeather is unavailable and the database fallback failed.",
        ) from None

    if cached_weather is not None:
        return cached_weather

    raise HTTPException(
        status_code=503,
        detail=(
            "OpenWeather is unavailable and no database observation "
            "was found within 30 km of these coordinates."
        ),
    )
