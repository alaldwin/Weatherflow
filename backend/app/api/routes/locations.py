from fastapi import APIRouter, HTTPException, Query

from app.services.openweather import (
    OpenWeatherError,
    search_locations,
)

router = APIRouter(
    prefix="/api/v1/locations",
    tags=["Locations"],
)


@router.get("/search")
async def locations_search(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=5, ge=1, le=10),
):
    try:
        data = await search_locations(q, limit)

        return {
            "query": q,
            "count": len(data),
            "data": data,
        }

    except OpenWeatherError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
