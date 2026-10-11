{{
    config(
        materialized='view'
    )
}}

WITH ranked_weather AS (
    SELECT
        city,
        latitude,
        longitude,
        temperature,
        humidity,
        pressure,
        weather_description,
        wind_speed,
        source,
        observation_time,
        ingested_time,
        city_id,
        country,
        timezone,
        base,
        weather_id,
        weather_main,
        weather_icon,
        feels_like,
        temp_min,
        temp_max,
        sea_level,
        ground_level,
        visibility,
        wind_direction,
        wind_gust,
        rain_1h,
        cloudiness,
        sunrise,
        sunset,
        cod,

        ROW_NUMBER() OVER (
            PARTITION BY city
            ORDER BY observation_time DESC
        ) AS row_num
    FROM {{ ref('stg_weather_observations')}}
)

SELECT
    city,
    latitude,
    longitude,
    temperature,
    humidity,
    pressure,
    weather_description,
    wind_speed,
    source,
    observation_time,
    ingested_time,
    city_id,
    country,
    timezone,
    base,
    weather_id,
    weather_main,
    weather_icon,
    feels_like,
    temp_min,
    temp_max,
    sea_level,
    ground_level,
    visibility,
    wind_direction,
    wind_gust,
    rain_1h,
    cloudiness,
    sunrise,
    sunset,
    cod
FROM ranked_weather
WHERE row_num = 1