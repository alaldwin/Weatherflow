
from fastapi import APIRouter, HTTPException, Query

from app.core.logging_config import get_logger
from app.services.openweather import OpenWeatherError, search_locations
from app.services.city_catalog import CITIES

logger = get_logger(__name__, "locations.log")
router = APIRouter(prefix="/api/v1/locations", tags=["Locations"])


def search_local_locations(query: str, limit: int = 5) -> list[dict]:
    """Search the bundled city catalog without requiring internet access."""
    normalized_query = query.strip().casefold()
    matches = []

    for name, coordinates in CITIES.items():
        if normalized_query in name.casefold():
            matches.append(
                {
                    "name": name,
                    "state": None,
                    "country": "PH",
                    "lat": coordinates["latitude"],
                    "lon": coordinates["longitude"],
                }
            )

    return matches[:limit]


@router.get("/search")
async def locations_search(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=5, ge=1, le=10),
):
    query = q.strip()

    # Local search always works, even without internet.
    local_results = search_local_locations(query, limit)

    if local_results:
        logger.info(
            "Location search completed using local catalog",
            extra={"query": query, "result_count": len(local_results)},
        )
        return {
            "query": query,
            "count": len(local_results),
            "data": local_results,
            "source": "local",
        }

    # Try online geocoding when the local catalog has no match.
    try:
        online_results = await search_locations(query, limit)

        return {
            "query": query,
            "count": len(online_results),
            "data": online_results,
            "source": "openweather",
        }

    except OpenWeatherError as exc:
        logger.warning(
            "Online geocoding unavailable; returning no local matches",
            extra={"query": query, "error": str(exc)},
        )

        # Offline searches should not fail with HTTP 502.
        return {
            "query": query,
            "count": 0,
            "data": [],
            "source": "local",
        }

    except Exception as exc:
        logger.exception(
            "Unexpected location search error",
            extra={"query": query},
        )
        raise HTTPException(
            status_code=500,
            detail="Location search failed unexpectedly.",
        ) from exc
 