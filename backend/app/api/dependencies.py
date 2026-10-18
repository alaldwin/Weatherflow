from datetime import date
from typing import Annotated

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas.weather import DateFilters


class PaginationQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


def get_date_filters(
    city: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> DateFilters:

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be on or before end_date",
        )

    return DateFilters(
        city=city.strip() if city else None,
        start_date=start_date,
        end_date=end_date,
    )


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginationQuery:
    return PaginationQuery(
        limit=limit,
        offset=offset,
    )
