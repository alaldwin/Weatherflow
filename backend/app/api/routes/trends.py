
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

from app.schemas.weather import WeatherTrendsResponse

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)


@router.get("/trends", response_model=WeatherTrendsResponse)
def get_weather_trends(
    city: str | None = Query(default=None, min_length=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be before or equal to end_date.",
        )

    conditions = []
    params = {}

    if city:
        conditions.append("LOWER(city) = LOWER(:city)")
        params["city"] = city.strip()

    if start_date:
        conditions.append("observation_date >= :start_date")
        params["start_date"] = start_date

    if end_date:
        conditions.append("observation_date <= :end_date")
        params["end_date"] = end_date

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    query = text(f"""
        SELECT
            city,
            observation_date,
            avg_temperature,
            previous_avg_temperature,
            temperature_change,
            avg_humidity,
            previous_avg_humidity,
            humidity_change
        FROM mrt_dev.mrt_weather_trends
        {where_clause}
        ORDER BY observation_date DESC, city
        LIMIT 1000
    """)

    try:
        with engine.connect() as connection:
            result = connection.execute(query, params)
            rows = result.mappings().all()

        return {
            "count": len(rows),
            "filters": {
                "city": city,
                "start_date": start_date,
                "end_date": end_date,
            },
            "data": [dict(row) for row in rows],
        }

    except SQLAlchemyError as exc:
        print(f"Weather Trends Query Failed: {exc!r}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve weather trends.",
        ) from exc
