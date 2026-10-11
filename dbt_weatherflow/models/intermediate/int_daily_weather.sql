
{{
    config(
        materialized='view'
    )
}}

SELECT
    city,
    country,
    CAST(observation_time AS DATE) AS observation_date,

    ROUND(AVG(temperature)::NUMERIC, 2) AS avg_temperature,
    ROUND(MIN(temperature)::NUMERIC, 2) AS min_temperature,
    ROUND(MAX(temperature)::NUMERIC, 2) AS max_temperature,

    ROUND(AVG(feels_like)::NUMERIC, 2) AS avg_feels_like,
    ROUND(AVG(humidity)::NUMERIC, 2) AS avg_humidity,
    ROUND(AVG(pressure)::NUMERIC, 2) AS avg_pressure,
    ROUND(AVG(wind_speed)::NUMERIC, 2) AS avg_wind_speed,

    ROUND(AVG(cloudiness)::NUMERIC, 2) AS avg_cloudiness,

    COUNT(*) AS observation_count

FROM {{ ref('stg_weather_observations') }}

GROUP BY
    city,
    country,
    CAST(observation_time AS DATE)
