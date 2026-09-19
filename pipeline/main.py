from pipeline.ingestion.extract_api import extract_openweather_data, extract_weatherapi_data
from pipeline.ingestion.save_json import save_json
from pipeline.validation.weather_validator import WeatherValidator
from pipeline.transformation.weather_transform import WeatherTransform
from pipeline.loaded.load_postresql import (
    ensure_database_ready,
    get_database_target,
    load_postgresql,
)
from pipeline.loaded.save_parquet import save_parquet

from common.logging import get_logger
from config.cities import CITIES

logger = get_logger(__name__, "main.log")


def slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def main() -> int:
    """Extract, validate, transform, and load weather data for each city."""

    failed_loads: list[str] = []

    if ensure_database_ready():
        logger.info(f"PostgreSQL connection OK ({get_database_target()}).")
    else:
        logger.error(
            "Continuing without loading into PostgreSQL because the database is "
            "unreachable. Transformed data is still saved as JSON and Parquet."
        )

    for city, coordinates in CITIES.items():

        latitude = coordinates["latitude"]
        longitude = coordinates["longitude"]

        openweather_data = extract_openweather_data(latitude, longitude, city)
        weatherapi_data = extract_weatherapi_data(latitude, longitude, city)

        if openweather_data:

            try:
                WeatherValidator.validate_openweather(openweather_data)
                save_json(openweather_data, city, "openweather")

                transformed = WeatherTransform(openweather_data, "openweather").transform()
                save_parquet(transformed, slugify(city), "openweather")

                table_name = f"openweather_{slugify(city)}"
                try:
                    load_postgresql(transformed, table_name)
                except Exception as exc:
                    failed_loads.append(table_name)
                    logger.warning(f"Skipping PostgreSQL load for {city}: {exc}")

            except ValueError as exc:
                logger.warning(f"OpenWeather data invalid for {city}: {exc}")

        if weatherapi_data:

            try:
                WeatherValidator.validate_weatherapi(weatherapi_data)
                save_json(weatherapi_data, city, "weatherapi")

                transformed = WeatherTransform(weatherapi_data, "weatherapi").transform()
                save_parquet(transformed, slugify(city), "weatherapi")

                table_name = f"weatherapi_{slugify(city)}"
                try:
                    load_postgresql(transformed, table_name)
                except Exception as exc:
                    failed_loads.append(table_name)
                    logger.warning(f"Skipping PostgreSQL load for {city}: {exc}")

            except ValueError as exc:
                logger.warning(f"WeatherAPI data invalid for {city}: {exc}")

    if failed_loads:
        logger.error(
            f"Weather pipeline finished with {len(failed_loads)} failed table load(s): "
            f"{', '.join(failed_loads)}"
        )
        return 1

    logger.info("Weather pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
