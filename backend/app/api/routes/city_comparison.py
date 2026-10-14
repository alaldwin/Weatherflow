
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

from app.schemas.weather import CityComparisonResponse

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)


@router.get("/cities/compare", response_model=CityComparisonResponse)
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

        return {
            "count": len(rows),
            "sort": {
                "sort_by": sort_by,
                "order": order,
            },
            "data": [dict(row) for row in rows],
        }

    except SQLAlchemyError as exc:
        print(f"Weather City Comparison Query Failed {exc!r}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve city comparison data.",
        ) from exc
