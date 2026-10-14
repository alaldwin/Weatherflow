
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

from app.schemas.weather import DailyWeatherResponse

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)


@router.get("/daily", response_model=DailyWeatherResponse)
def get_daily_weather(
    city: str | None = Query(default=None, min_length=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be before or equal to end_date.",
        )

    query = text("""
        SELECT
            city,
            observation_date,
            avg_temperature,
            min_temperature,
            max_temperature,
            avg_feels_like,
            avg_humidity,
            avg_pressure,
            avg_wind_speed,
            avg_cloudiness,
            observation_count
        FROM mrt_dev.mrt_daily_weather
        WHERE (
            CAST(:city AS TEXT) IS NULL 
            OR LOWER(city) = LOWER(CAST(:city AS TEXT))
        )
        AND (
            CAST(:start_date AS DATE) IS NULL 
            OR observation_date >= CAST(:start_date AS DATE)
        )
        AND (
            CAST(:end_date AS DATE) IS NULL 
            OR observation_date <= CAST(:end_date AS DATE)
        )
        ORDER BY observation_date DESC, city
        LIMIT 1000;
    """)

    try:
        with engine.connect() as connection:
            result = connection.execute(
                query,
                {
                    "city": city.strip() if city else None,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
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
        print(f"Weather Query Failed: {exc!r}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve daily weather data.",
        ) from exc

