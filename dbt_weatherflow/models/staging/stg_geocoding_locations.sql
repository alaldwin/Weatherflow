{{
    config(
        materialized='table'
    )
}}

WITH stg_geocoding AS (

    SELECT *
    FROM {{ source('geocoding', 'geocoding_manila') }}

    UNION ALL

    SELECT *
    FROM {{ source('geocoding', 'geocoding_quezon_city') }}

    UNION ALL

    SELECT *
    FROM {{ source('geocoding', 'geocoding_cebu_city') }}

    UNION ALL

    SELECT *
    FROM {{ source('geocoding', 'geocoding_davao_city') }}

    UNION ALL

    SELECT *
    FROM {{ source('geocoding', 'geocoding_baguio') }}

    UNION ALL

    SELECT *
    FROM {{ source('geocoding', 'geocoding_iloilo_city') }}

    UNION ALL

    SELECT *
    FROM {{ source('geocoding', 'geocoding_cagayan_de_oro') }}

    UNION ALL

    SELECT *
    FROM {{ source('geocoding', 'geocoding_zamboanga_city') }}

)

SELECT
    city,
    latitude,
    longitude,
    country,
    state
FROM stg_geocoding