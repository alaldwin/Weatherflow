SELECT *
FROM {{ ref('stg_weather_observations') }}
WHERE
    (temperature < -100 OR temperature > 70)
    OR (humidity < 0 OR humidity > 100)
    OR wind_speed < 0
    OR latitude < -90
    OR latitude > 90
    OR longitude < -180
    OR longitude > 180
