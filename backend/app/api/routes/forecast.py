
from fastapi import APIRouter, HTTPException, Query

from app.services.openweather import (
    OpenWeatherError,
    get_forecast,
)

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
        return await get_forecast(lat, lon, days)

    except OpenWeatherError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
