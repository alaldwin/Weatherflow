from fastapi import APIRouter, HTTPException, Query

from app.core.logging_config import get_logger
from app.services.openweather import (
    OpenWeatherError,
    search_locations,
)

logger = get_logger(__name__, "locations.log")

router = APIRouter(
    prefix="/api/v1/locations",
    tags=["Locations"],
)


@router.get("/search")
async def locations_search(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=5, ge=1, le=10),
):
    logger.info(
        "Location search request received",
        extra={
            "query": q,
            "limit": limit,
        },
    )

    try:
        logger.debug(
            "Calling OpenWeather geocoding service",
            extra={
                "query": q,
                "limit": limit,
            },
        )

        data = await search_locations(q, limit)

        logger.info(
            "Location search completed successfully",
            extra={
                "query": q,
                "result_count": len(data),
            },
        )

        if not data:
            logger.warning(
                "Location search returned no results",
                extra={"query": q},
            )

        return {
            "query": q,
            "count": len(data),
            "data": data,
        }

    except OpenWeatherError as exc:
        logger.error(
            "OpenWeather location search failed",
            extra={
                "query": q,
                "error": str(exc),
            },
        )

        raise HTTPException(
            status_code=502,
            detail="Location search service is temporarily unavailable.",
        ) from exc

    except Exception:
        logger.exception(
            "Unexpected error during location search",
            extra={"query": q},
        )
        raise