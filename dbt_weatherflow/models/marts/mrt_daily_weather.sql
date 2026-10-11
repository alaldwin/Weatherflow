
{{
    config(
        materialized='table'
    )
}}

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

FROM {{ ref('int_daily_weather') }}

