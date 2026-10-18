
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging_config import get_logger
from app.db.session import engine
from app.schemas.weather import CityComparisonResponse

logger = get_logger(__name__, "comprison.log")

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)



@router.get(
    "/cities/compare",
    response_model=CityComparisonResponse,
    summary="Compare weather across cities",
    description=(
        "Returns city-level weather data with temperature rankings "
        "and differences from the average. Supports sorting and pagination."
    ),
    responses={
        200: {"description": "City comparison data retrieved successfully."},
        422: {"description": "An invalid sort field, sort order, or query parameter was supplied."},
        503: {"description": "The database is unavailable."},
    },
)
def compare_cities(
    sort_by: str = Query(
        default="temperature",
        pattern="^(temperature|humidity|wind_speed|city)$",
    ),
    order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
    ),
):

    logger.info("City comprison request received | sort_by%s | order=%s", sort_by, order)

    # Map accepted parameters to fixed SQL column names.
    sort_columns = {
        "temperature": "temperature",
        "humidity": "humidity",
        "wind_speed": "wind_speed",
        "city": "city",
    }

    sort_column = sort_columns[sort_by]
    sort_direction = order.upper()

    query = text(f"""
        SELECT
            city,
            temperature,
            feels_like,
            humidity,
            pressure,
            wind_speed,
            cloudiness,
            weather_main,
            weather_description,
            observation_time,
            temperature_rank,
            average_city_temperature,
            difference_from_average
        FROM mrt_dev.mrt_city_comparison
        ORDER BY {sort_column} {sort_direction} NULLS LAST,
                 city ASC
        LIMIT 100;
    """)

    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            rows = result.mappings().all()


        logger.info("City comparison query successful | rows_returned=%d | sort_by=%s | order=%s", len(rows), sort_by, order)

        return {
            "count": len(rows),
            "sort": {
                "sort_by": sort_by,
                "order": order,
            },
            "data": [dict(row) for row in rows],
        }

    except SQLAlchemyError as exc:
        logger.exception(
            "City comparison database query failed | "
            "sort_by=%s | order=%s",
            sort_by,
            order,
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve city comparison data.",
        ) from exc
