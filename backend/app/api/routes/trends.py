
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine
from app.schemas.weather import WeatherTrendsResponse
from app.api.dependencies import (
    WeatherDateFilters,
    PaginationQuery,
    get_date_filters,
    get_pagination,
)

from app.core.logging_config import get_logger


logger = get_logger(__name__, "weather_trends.log")

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)



@router.get(
    "/trends",
    response_model=WeatherTrendsResponse,
    summary="Get weather trends",
    description=(
        "Returns daily temperature and humidity trends, including "
        "previous values and changes. Supports optional city and date filters."
    ),
    responses={
        200: {"description": "Weather trends retrieved successfully."},
        422: {"description": "Query parameters are invalid."},
        503: {"description": "The database is unavailable."},
    },
)
def get_weather_trends(
    filters: Annotated[WeatherDateFilters, Depends(get_date_filters)],
    pagination: Annotated[PaginationQuery, Depends(get_pagination)],
):
    limit = pagination.limit
    offset = pagination.offset

    city = filters.city
    start_date = filters.start_date
    end_date = filters.end_date

    logger.info(
        "Weather trends request received | city=%s | "
        "start_date=%s | end_date=%s | limit=%d | offset=%d",
        city,
        start_date,
        end_date,
        limit,
        offset,
    )

    conditions = []
    params = {
        "fetch_limit": limit + 1,
        "offset": offset,
    }

    if city:
        conditions.append("LOWER(city) = LOWER(:city)")
        params["city"] = city.strip()

        logger.debug(
            "Weather trends city filter applied | city=%s",
            city,
        )

    if start_date:
        conditions.append("observation_date >= :start_date")
        params["start_date"] = start_date

        logger.debug(
            "Weather trends start date filter applied | start_date=%s",
            start_date,
        )

    if end_date:
        conditions.append("observation_date <= :end_date")
        params["end_date"] = end_date

        logger.debug(
            "Weather trends end date filter applied | end_date=%s",
            end_date,
        )


    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    logger.debug(
        "Weather trends SQL query prepared | filters_applied=%d",
        len(conditions),
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
            logger.debug("Executing weather trends database query")

            result = connection.execute(query, params)
            rows = result.mappings().all()

        logger.debug(
            "Weather trends query executed | fetched_rows=%d",
            len(rows),
        )

        has_more = len(rows) > limit
        data = [dict(row) for row in rows[:limit]]

        logger.info(
            "Weather trends retrieved successfully | "
            "count=%d | has_more=%s | limit=%d | offset=%d",
            len(data),
            has_more,
            limit,
            offset,
        )

        if not data:
            logger.warning(
                "No weather trends records found | city=%s | "
                "start_date=%s | end_date=%s",
                city,
                start_date,
                end_date,
            )

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
        logger.exception(
            "Weather trends database query failed | "
            "city=%s | start_date=%s | end_date=%s | "
            "limit=%d | offset=%d",
            city,
            start_date,
            end_date,
            limit,
            offset,
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve weather trends.",
        ) from exc
