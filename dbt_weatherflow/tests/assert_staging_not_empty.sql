SELECT 1 AS failure
WHERE NOT EXISTS (
SELECT 1
FROM {{ ref('stg_weather_observations') }}
)
