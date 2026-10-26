from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging_config import get_logger
from app.db.session import engine
from app.schemas.weather import CurrentWeather, CurrentWeatherListResponse

logger = get_logger(__name__, "current_weather.log")

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)


@router.get(
    "/current",
    response_model=CurrentWeatherListResponse,
    tags=["Current Weather"],
    summary="Get current weather for all cities",
    description=(
        "Returns the latest available weather records from the "
        "current-weather analytics mart. Supports pagination."
    ),
    responses={
        200: {"description": "Weather records retrieved successfully."},
        503: {"description": "The database is unavailable."},
    },
)
def get_current_weather(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):

    logger.info(
        "Current weather list request received | limit=%d | offset=%d",
        limit,
        offset,
    )

    logger.debug(
        "Preparing current weather list query | "
        "table=mrt_dev.mrt_current_weather | limit=%d | offset=%d",
        limit,
        offset,
    )

    query = text("""
        SELECT
            city,
            country,
            latitude,
            longitude,
            temperature,
            feels_like,
            temp_min,
            temp_max,
            humidity,
            pressure,
            visibility,
            wind_speed,
            wind_direction,
            wind_gust,
            cloudiness,
            weather_main,
            weather_description,
            weather_icon,
            observation_time,
            sunrise,
            sunset
        FROM mrt_dev.mrt_current_weather
        ORDER BY city
        LIMIT :fetch_limit OFFSET :offset
    """)

    try:
        with engine.connect() as connection:
            result = connection.execute(
                query, {"fetch_limit": limit + 1, "offset": offset}
            )
            rows = [dict(row) for row in result.mappings().all()]

        logger.debug(
            "Current weather query executed | fetched_rows=%d",
            len(rows),
        )

        has_more = len(rows) > limit
        rows = rows[:limit]

        logger.info(
            "Current weather list retrieved successfully | "
            "count=%d | limit=%d | offset=%d | has_more=%s",
            len(rows),
            limit,
            offset,
            has_more,
        )

        if not rows:
            logger.warning(
                "Current weather list returned no records | limit=%d | offset=%d",
                limit,
                offset,
            )

        return {
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "data": rows,
        }

    except SQLAlchemyError:
        logger.exception(
            "Failed to retrieve current weather list | limit=%d | offset=%d",
            limit,
            offset,
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve current weather data.",
        )



@router.get(
    "/current/{city}",
    response_model=CurrentWeather,
    summary="Get current weather for one city",
    description="Returns the latest available weather record for the specified city.",
    responses={
        200: {"description": "Weather record retrieved successfully."},
        404: {"description": "No weather record was found for the city."},
        503: {"description": "The database is unavailable."},
    },
)

def get_current_weather_by_city(city: str):

    city = city.strip()

    logger.info(
        "Current weather by city request received | city=%s",
        city,
    )

    logger.debug(
        "Preparing city weather query | table=mrt_dev.mrt_current_weather | city=%s",
        city,
    )

    query = text(""" 
        SELECT 
            city, 
            country, 
            latitude, 
            longitude, 
            temperature, 
            feels_like, 
            temp_min, 
            temp_max, 
            humidity, 
            pressure, 
            visibility, 
            wind_speed, 
            wind_direction, 
            wind_gust, 
            cloudiness, 
            weather_main, 
            weather_description, 
            weather_icon, 
            observation_time, 
            sunrise, 
            sunset 
        FROM mrt_dev.mrt_current_weather 
        WHERE LOWER(city) = LOWER(:city) 
        LIMIT 1; 
    """)

    try:
        with engine.connect() as connection:
            logger.debug(
                "Executing city weather query | city=%s",
                city,
            )

            result = connection.execute(
                query,
                {"city": city.strip()},
            )
            row = result.mappings().first()

        if row is None:
            logger.warning(
                "Current weather data not found | city=%s",
                city,
            )
            raise HTTPException(
                status_code=404,
                detail=f"No Current Weather Data Not Found for City '{city}'.",
            )

        logger.info(
            "Current weather retrieved successfully | city=%s",
            city,
        )

        logger.debug(
            "Returning current weather response | city=%s",
            city,
        )

        return dict(row)

    except SQLAlchemyError:
        logger.exception(
            "Failed to retrieve current weather by city | city=%s",
            city,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Unable to retrieve current weather data.",
            },
        )
