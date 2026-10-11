SELECT
    city,
    source,
    observation_time,
    COUNT(*) AS duplicate_count
FROM {{ ref('stg_weather_observations') }}
GROUP BY
    city,
    source,
    observation_time
HAVING COUNT(*) > 1
