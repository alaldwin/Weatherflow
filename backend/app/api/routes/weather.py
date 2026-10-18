
from fastapi import APIRouter, HTTPException, Query

from app.services.openweather import (
    OpenWeatherError,
    get_current_weather,
)

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)


@router.get("/current")
async def current_weather(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
):
    try:
        return await get_current_weather(lat, lon)

    except OpenWeatherError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

