import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.forecast_cache import load_forecast, save_forecast
from app.services.openweather import OpenWeatherError, get_forecast

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather Forecast"],
)


@router.get("/forecast")
async def weather_forecast(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    days: int = Query(default=5, ge=1, le=5),
):
    try:
        forecast = await get_forecast(lat, lon, days)
        return save_forecast(lat, lon, forecast)

    except OpenWeatherError as exc:
        cached = load_forecast(lat, lon)

        if cached is not None:
            logger.warning(
                "OpenWeather unavailable; serving cached forecast for %.2f, %.2f",
                lat,
                lon,
            )

            # Respect the requested number of days.
            cached["hourly"] = cached.get("hourly", [])[: days * 8]
            cached["daily"] = cached.get("daily", [])[:days]
            cached["source"] = "Cached OpenWeather forecast"
            return cached

        raise HTTPException(
            status_code=502,
            detail=(
                "OpenWeather is unavailable and no cached forecast exists "
                "for these coordinates."
            ),
        ) from exc
