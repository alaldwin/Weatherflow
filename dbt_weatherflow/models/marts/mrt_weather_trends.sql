
{{
    config(
        materialized='table'
    )
}}

WITH daily_trends AS (

    SELECT
        city,
        observation_date,
        avg_temperature,
        avg_humidity,

        LAG(avg_temperature) OVER (
            PARTITION BY city
            ORDER BY observation_date
        ) AS previous_avg_temperature,

        LAG(avg_humidity) OVER (
            PARTITION BY city
            ORDER BY observation_date
        ) AS previous_avg_humidity

    FROM {{ ref('int_daily_weather') }}

)

SELECT
    city,
    observation_date,
    avg_temperature,
    previous_avg_temperature,

    ROUND(
        (avg_temperature - previous_avg_temperature)::NUMERIC,
        2
    ) AS temperature_change,

    avg_humidity,
    previous_avg_humidity,

    ROUND(
        (avg_humidity - previous_avg_humidity)::NUMERIC,
        2
    ) AS humidity_change

FROM daily_trends

