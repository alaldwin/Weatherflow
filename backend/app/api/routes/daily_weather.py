from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import (
    PaginationQuery,
    get_date_filters,
    get_pagination,
)
from app.core.logging_config import get_logger
from app.db.session import engine
from app.schemas.weather import DailyWeatherResponse, DateFilters

logger = get_logger(__name__, "daily_weather.log")


router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)


@router.get(
    "/daily",
    response_model=DailyWeatherResponse,
    summary="Get daily weather summaries",
    description=(
        "Returns daily weather aggregates. Optionally filter by city, "
        "start date, and end date. Supports pagination."
    ),
    responses={
        200: {"description": "Daily weather summaries retrieved successfully."},
        422: {
            "description": "Query parameters are invalid, including an invalid date range."
        },
        503: {"description": "The database is unavailable."},
    },
)
def get_daily_weather(
    filters: Annotated[DateFilters, Depends(get_date_filters)],
    pagination: Annotated[PaginationQuery, Depends(get_pagination)],
):
    limit = pagination.limit
    offset = pagination.offset

    logger.info(
        "Daily weather request received | city=%s | "
        "start_date=%s | end_date=%s | limit=%d | offset=%d",
        filters.city,
        filters.start_date,
        filters.end_date,
        limit,
        offset,
    )

    conditions = []
    params = {
        "fetch_limit": limit + 1,
        "offset": offset,
    }

    if filters.city:
        conditions.append("LOWER(city) = LOWER(:city)")
        params["city"] = filters.city

    if filters.start_date:
        conditions.append("observation_date >= :start_date")
        params["start_date"] = filters.start_date
        logger.debug(
            "Daily weather start date filter applied | start_date=%s",
            filters.start_date,
        )

    if filters.end_date:
        conditions.append("observation_date <= :end_date")
        params["end_date"] = filters.end_date
        logger.debug(
            "Daily weather end date filter applied | end_date=%s",
            filters.end_date,
        )

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    logger.debug(
        "Daily weather SQL query prepared | filters_applied=%d",
        len(conditions),
    )

    query = text(f"""
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
        {where_clause}
        ORDER BY observation_date DESC, city
        LIMIT :fetch_limit OFFSET :offset
    """)

    try:
        with engine.connect() as connection:
            logger.debug("Executing daily weather database query")

            result = connection.execute(query, params)
            rows = result.mappings().all()

        logger.debug(
            "Daily weather query executed | fetched_rows=%d",
            len(rows),
        )

        has_more = len(rows) > limit
        data = [dict(row) for row in rows[:limit]]

        logger.info(
            "Daily weather query successful | count=%d | "
            "has_more=%s | limit=%d | offset=%d",
            len(data),
            has_more,
            limit,
            offset,
        )

        if not data:
            logger.warning(
                "No daily weather records found | city=%s | "
                "start_date=%s | end_date=%s",
                filters.city,
                filters.start_date,
                filters.end_date,
            )

        return {
            "count": len(data),
            "filters": {
                "city": filters.city,
                "start_date": filters.start_date,
                "end_date": filters.end_date,
            },
            "data": data,
        }

    except SQLAlchemyError:
        logger.exception(
            "Failed to retrieve daily weather data | "
            "city=%s | start_date=%s | end_date=%s | "
            "limit=%d | offset=%d",
            filters.city,
            filters.start_date,
            filters.end_date,
            limit,
            offset,
        )

        raise HTTPException(
            status_code=503,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Unable to retrieve daily weather data.",
            },
        )
