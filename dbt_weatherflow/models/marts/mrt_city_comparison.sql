
{{
    config(
        materialized='table'
    )
}}

SELECT
    city,
    country,
    temperature,
    feels_like,
    humidity,
    pressure,
    wind_speed,
    cloudiness,
    weather_main,
    weather_description,
    observation_time,

    RANK() OVER (
        ORDER BY temperature DESC
    ) AS temperature_rank,

    ROUND(
        AVG(temperature) OVER ()::NUMERIC,
        2
    ) AS average_city_temperature,

    ROUND(
        (temperature - AVG(temperature) OVER ())::NUMERIC,
        2
    ) AS difference_from_average

FROM {{ ref('int_city_weather') }}

