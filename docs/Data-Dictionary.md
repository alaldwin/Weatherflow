# WeatherFlow Data Dictionary

This document describes the weather and geocoding data used by WeatherFlow, from the OpenWeather API payloads through the city-specific PostgreSQL source tables and dbt models.

> **Schema accuracy note:** This dictionary documents the known WeatherFlow design and the standard OpenWeather fields that the pipeline consumes. Confirm exact PostgreSQL column names, types, nullability, and transformations against the current `WeatherTransform`, geocoding transformation, loader, and database schema before treating this as a production schema contract. The table names below reflect the project's eight-city, city-specific design; they are not a substitute for inspecting the live database.

## 1. Naming and data types

- **Source payload** means a field returned by OpenWeather before WeatherFlow transforms it.
- **Transformed column** means the flattened/renamed value written by the pipeline. The exact destination name may differ from the API field path.
- Types in this document are logical types, not confirmed PostgreSQL declarations.
- Temperatures from OpenWeather are in **Kelvin by default** unless the request explicitly specifies another unit. Check the API request and transformation before assuming a stored temperature is Celsius.
- API timestamps such as `dt`, `sunrise`, and `sunset` are Unix timestamps in seconds. A transformed column may store them as a timestamp instead.

## 2. Weather observation data

The Current Weather API returns a weather snapshot for a location. WeatherFlow extracts the payload, validates/transforms it, writes a Parquet representation, and appends new observations to a city-specific PostgreSQL source table.

### 2.1 Common weather fields

| API field / path | Meaning | Logical type | Notes |
|---|---|---|---|
| `coord.lon` | Longitude of the observed location | Decimal | Geographic coordinate; normally between -180 and 180. |
| `coord.lat` | Latitude of the observed location | Decimal | Geographic coordinate; normally between -90 and 90. |
| `weather[].id` | OpenWeather condition code | Integer | Numeric provider code for the weather condition. |
| `weather[].main` | Short condition category | String | For example, `Rain` or `Clouds`. |
| `weather[].description` | Human-readable condition description | String | Provider-supplied text; capitalization can vary. |
| `weather[].icon` | Provider weather-icon code | String | Can be used to map or display a weather icon. |
| `base` | Internal provider station/base indicator | String | Often not required for application analytics. |
| `main.temp` | Current air temperature | Decimal | Unit depends on API request; Kelvin by default. |
| `main.feels_like` | Apparent temperature | Decimal | Unit follows the API temperature unit. |
| `main.temp_min` | Minimum temperature reported for the location | Decimal | Provider-defined meaning; not necessarily a daily minimum. |
| `main.temp_max` | Maximum temperature reported for the location | Decimal | Provider-defined meaning; not necessarily a daily maximum. |
| `main.pressure` | Atmospheric pressure at sea level | Integer | Commonly hPa. |
| `main.humidity` | Relative humidity | Integer | Percentage, normally 0–100. |
| `main.sea_level` | Atmospheric pressure at sea level, when supplied | Integer | Optional provider field. |
| `main.grnd_level` | Atmospheric pressure at ground level, when supplied | Integer | Optional provider field. |
| `visibility` | Visibility distance | Integer | Commonly metres; may be absent or capped by provider. |
| `wind.speed` | Wind speed | Decimal | Unit depends on API request; metres/second by default. |
| `wind.deg` | Wind direction | Integer | Degrees clockwise from north, generally 0–360. |
| `wind.gust` | Wind gust speed, when supplied | Decimal | Optional; unit follows wind-speed unit. |
| `clouds.all` | Cloudiness | Integer | Percentage, normally 0–100. |
| `dt` | Observation time | Integer | Unix epoch seconds; useful for freshness and deduplication. |
| `sys.type` | Provider system type | Integer | Optional provider metadata. |
| `sys.id` | Provider system identifier | Integer | Optional provider metadata. |
| `sys.country` | Country code | String | For Philippine city records, expected to identify the Philippines. Verify the exact code used by the API. |
| `sys.sunrise` | Sunrise time | Integer | Unix epoch seconds. |
| `sys.sunset` | Sunset time | Integer | Unix epoch seconds. |
| `timezone` | Time-zone offset in seconds from UTC | Integer | Offset value, not a named IANA time zone. |
| `id` | OpenWeather city/location identifier | Integer | Provider identifier; not necessarily WeatherFlow's own primary key. |
| `name` | Provider-reported city name | String | May differ in spelling or formatting from the configured city name. |
| `cod` | Provider response code | Integer or string | Response metadata; confirm whether the pipeline persists it. |

### 2.2 Weather table grain

The intended grain of a weather source table is **one stored observation for a configured city and observation time**. The pipeline checks the weather payload's `dt` value against its state/checkpoint before loading the weather observation.

A checkpoint check is not by itself a database uniqueness constraint. If a task retries after a database insert but before checkpoint state is updated, duplicate rows can still occur unless the database load is idempotent. Inspect the actual schema and loader before assuming that `(city, observation_time)` is enforced as unique.

### 2.3 City-specific weather source tables

WeatherFlow retains separate source tables for each configured city:

| City | PostgreSQL source table |
|---|---|
| Manila | `openweather_manila` |
| Quezon City | `openweather_quezon_city` |
| Cebu City | `openweather_cebu_city` |
| Davao City | `openweather_davao_city` |
| Baguio | `openweather_baguio` |
| Iloilo City | `openweather_iloilo_city` |
| Cagayan de Oro | `openweather_cagayan_de_oro` |
| Zamboanga City | `openweather_zamboanga_city` |

The precise columns in these tables depend on the current weather transformation and loader. The API paths in §2.1 describe the source semantics; they do not assert that nested names such as `main.temp` are literal PostgreSQL column names.

## 3. Geocoding data

WeatherFlow uses OpenWeather Geocoding to resolve a place name to coordinates and related location metadata. Coordinates can support city identification and weather lookup by latitude/longitude.

### 3.1 Geocoding fields

| API field / path | Meaning | Logical type | Notes |
|---|---|---|---|
| `name` | Resolved place name | String | Provider's canonical/display name; may not exactly match the search query. |
| `local_names` | Localized names for the place, when supplied | JSON object | Optional and language-keyed; may be omitted from the transformed table. |
| `lat` | Latitude | Decimal | Normally between -90 and 90. |
| `lon` | Longitude | Decimal | Normally between -180 and 180. |
| `country` | Country code | String | Provider-supplied country identifier. |
| `state` | State, province, or administrative region, when supplied | String | Optional; availability varies by place. |

### 3.2 Geocoding table grain and source tables

A geocoding response represents a resolved place, not a time-series weather observation. A practical natural key may include coordinates plus country and administrative/place name, but the correct uniqueness rule depends on the exact payload and intended treatment of duplicate place names. Do not assume `name` alone is unique.

The project uses city-specific geocoding source tables:

| City | PostgreSQL source table |
|---|---|
| Manila | `geocoding_manila` |
| Quezon City | `geocoding_quezon_city` |
| Cebu City | `geocoding_cebu_city` |
| Davao City | `geocoding_davao_city` |
| Baguio | `geocoding_baguio` |
| Iloilo City | `geocoding_iloilo_city` |
| Cagayan de Oro | `geocoding_cagayan_de_oro` |
| Zamboanga City | `geocoding_zamboanga_city` |

**Current pipeline behavior to verify:** the geocoding records are loaded with append behavior before the weather observation checkpoint check. Unless the loader or database schema prevents duplicates, repeated hourly runs can append the same geocoding result again. Because geocoding is reference-like data, consider an upsert or deduplication strategy after confirming the actual columns and stable key.

## 4. dbt model layers

WeatherFlow's dbt project separates source data from models intended for analytics and application consumption. The following model names are known in the project; their output columns should be read from the current SQL model files and schema.yml files rather than inferred from the API payload alone.

| Layer | Known model | Purpose |
|---|---|---|
| Staging | `stg_weather_observations` | Standardize/rename weather source fields for downstream models. |
| Staging | `stg_geocoding_locations` | Standardize location and coordinate fields. |
| Intermediate | `int_city_weather` | Prepare city-level weather records for marts. |
| Intermediate | `int_daily_weather` | Prepare daily-grain weather aggregates. |
| Mart | `mrt_current_weather` | Current/latest weather view for consumption. |
| Mart | `mrt_daily_weather` | Daily weather metrics for charts and summaries. |
| Mart | `mrt_weather_trends` | Trend-oriented weather metrics over time. |
| Mart | `mrt_city_comparison` | Cross-city comparison metrics. |

For an exact mart-level dictionary, document each model's selected columns, SQL expressions, output type, and business meaning directly from its `.sql` and YAML files. In particular, distinguish an API field from a derived metric such as a daily average, maximum, minimum, or trend.

## 5. Data quality and interpretation rules

- **Coordinates:** validate latitude and longitude ranges; reject or quarantine impossible values.
- **Temperature and wind units:** record the configured OpenWeather units and the conversion logic, if any. Never label values as Celsius or km/h without confirming the request/transformation.
- **Humidity and cloudiness:** validate expected percentage ranges of 0–100 when values are present.
- **Observation time:** convert epoch seconds consistently and document the timezone used for display. Preserve the original timestamp when useful for auditability.
- **Optional fields:** `wind.gust`, `main.sea_level`, `main.grnd_level`, `sys.sunrise`, `sys.sunset`, `state`, and `local_names` may be absent. Decide whether absence is stored as `NULL`, omitted from JSON, or handled by validation.
- **Provider names and city names:** use configured city identifiers consistently; do not rely on free-text names alone to join weather and geocoding records.
- **Duplicates:** checkpoint state and append loading do not guarantee database-level idempotency. Prefer an explicit stable key and conflict-handling strategy after verifying the table schema.
- **Lineage:** keep source/API field names traceable through transformation columns and dbt models.

## 6. How to verify the live PostgreSQL schema

Run these commands from the project directory. The host port is shown as `5433` in the project's Docker Compose setup; adjust credentials if your `.env` differs.

```bash
# List relations in the current schema
 docker compose exec db psql -U weatherflow -d weatherflow -X -P pager=off -c "\\dt"

# Inspect one weather source table
 docker compose exec db psql -U weatherflow -d weatherflow -X -P pager=off -c "\\d+ openweather_manila"

# Inspect one geocoding source table
 docker compose exec db psql -U weatherflow -d weatherflow -X -P pager=off -c "\\d+ geocoding_manila"

# List columns, types, nullability, and defaults for all city-specific source tables
 docker compose exec db psql -U weatherflow -d weatherflow -X -P pager=off -c "
SELECT table_schema, table_name, ordinal_position, column_name,
       data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name LIKE 'openweather_%'
   OR table_name LIKE 'geocoding_%'
ORDER BY table_schema, table_name, ordinal_position;
"
```

If `docker compose exec db` is not the service name in your current Compose file, run `docker compose ps` and substitute the actual PostgreSQL service name. If the database uses a different schema, include the schema in your inspection queries.

## 7. How to verify dbt output columns

From the project root, inspect the model SQL and YAML definitions:

```bash
find dbt_weatherflow/models -type f \( -name '*.sql' -o -name '*.yml' -o -name '*.yaml' \) -print
```

Then open the relevant model and schema YAML. To inspect columns materialized in PostgreSQL, query `information_schema.columns` for the model's actual schema and table name (for example, `mrt_dev.mrt_current_weather`). Confirm whether each model is a table or view before planning schema changes.

## 8. Suggested column-level dictionary template

Use this template when confirming the exact physical schema:

| Column | PostgreSQL type | Nullable? | Definition / business meaning | Source / expression | Example | Quality rule |
|---|---|---|---|---|---|---|
| `<actual_column>` | `<actual_type>` | Yes/No | What the value represents | API path or dbt SQL expression | `<example>` | Range, accepted values, uniqueness, or freshness check |

Update this document whenever a transformation, API field, source table, or dbt model contract changes.
