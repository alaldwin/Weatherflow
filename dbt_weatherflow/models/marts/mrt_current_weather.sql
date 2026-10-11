
{{
    config(
        materialized='table'
    )
}}

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

FROM {{ ref('int_city_weather') }}

