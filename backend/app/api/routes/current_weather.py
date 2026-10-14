
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

from app.schemas.weather import CurrentWeather, CurrentWeatherListResponse

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["Weather"],
)


@router.get("/current", response_model=CurrentWeatherListResponse)
def get_current_weather():
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
        ORDER BY city;
    """)

    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            rows = result.mappings().all()

        return {
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve current weather data.",
        )

@router.get("/current/{city}", response_model=CurrentWeather,)
def get_current_weather_by_city(city: str):
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
            result = connection.execute(
                query,
                {"city": city.strip()},
            )
            row = result.mappings().first()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"No Current Weather Data Not Found for City '{city}'.",
            )
        
        return dict(row)

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve current weather data.",
        )