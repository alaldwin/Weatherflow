import re

from common.logging import get_logger
from config.cities import CITIES

from pipeline.ingestion.extract_api import (
    extract_geocoding_data,
    extract_openweather_data,
)
from pipeline.ingestion.save_json import save_json
from pipeline.ingestion.state_manager import is_new_data, update_state
from pipeline.loaded.load_postresql import load_postgresql
from pipeline.loaded.save_parquet import save_parquet
from pipeline.transformation.weather_transform import WeatherTransform

logger = get_logger(__name__, "main.log")


def _table_name(prefix: str, city: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", city.lower()).strip("_")
    return f"{prefix}_{slug}"


def main() -> int:
    """Run the weather pipeline and report failures to Airflow."""

    logger.info("Starting Weather Ingestion...")

    successful_cities = []
    skipped_cities = []
    failed_cities = []

    for city, coordinates in CITIES.items():
        latitude = coordinates["latitude"]
        longitude = coordinates["longitude"]

        logger.info("Processing city: %s", city)

        try:
            # 1. Extract current weather
            weather_data = extract_openweather_data(
                latitude, longitude, city
            )

            if not weather_data:
                raise ValueError(
                    f"No weather data returned for {city}"
                )

            # 2. Extract and load geocoding data
            geocoding_data = extract_geocoding_data(
                latitude, longitude, city
            )

            if geocoding_data:
                geocoding_df = WeatherTransform(
                    geocoding_data, "geocoding"
                ).transform()

                if not geocoding_df.is_empty():
                    geocoding_table = _table_name(
                        "geocoding", city
                    )

                    load_postgresql(
                        geocoding_df,
                        table_name=geocoding_table,
                        if_exists="append",
                    )

                    logger.info(
                        "Geocoding loaded for %s into %s",
                        city,
                        geocoding_table,
                    )
                else:
                    logger.warning(
                        "Geocoding transformation was empty for %s",
                        city,
                    )
            else:
                # Geocoding is optional here; weather ingestion can continue.
                logger.warning(
                    "No geocoding data returned for %s", city
                )

            # 3. Check incremental-load state
            observation_time = weather_data.get("dt")

            if observation_time is None:
                raise ValueError(
                    f"Missing observation timestamp for {city}"
                )

            if not is_new_data(
                source="openweather",
                location=city,
                observation_time=observation_time,
            ):
                logger.info(
                    "No new weather data for %s. Skipping.", city
                )
                skipped_cities.append(city)
                continue

            # 4. Save raw JSON
            output_file = save_json(
                data=weather_data,
                city=city,
                source="openweather",
            )

            if output_file is None:
                raise RuntimeError(
                    f"Raw JSON was not saved for {city}"
                )

            logger.info(
                "Raw JSON saved for %s: %s",
                city,
                output_file,
            )

            # 5. Transform weather data
            weather_df = WeatherTransform(
                weather_data, "openweather"
            ).transform()

            if weather_df.is_empty():
                raise ValueError(
                    f"Weather transformation produced no data for {city}"
                )

            logger.info(
                "Weather data transformed for %s", city
            )

            # 6. Save Parquet
            parquet_file = save_parquet(
                weather_df, city, "openweather"
            )

            if parquet_file is None:
                raise RuntimeError(
                    f"Parquet file was not saved for {city}"
                )

            logger.info(
                "Parquet saved for %s: %s",
                city,
                parquet_file,
            )

            # 7. Load PostgreSQL
            table_name = _table_name("openweather", city)

            loaded_rows = load_postgresql(
                weather_df,
                table_name=table_name,
                if_exists="append",
            )

            logger.info(
                "Loaded %d row(s) for %s into %s.",
                loaded_rows,
                city,
                table_name,
            )

            # 8. Update checkpoint only after the database load succeeds
            update_state(
                source="openweather",
                location=city,
                observation_time=observation_time,
            )

            logger.info("Checkpoint updated for %s.", city)
            successful_cities.append(city)

        except Exception:
            logger.exception("Failed to process city: %s", city)
            failed_cities.append(city)

    # 9. Report the final result
    logger.info(
        "Pipeline summary | total=%d | loaded=%d | skipped=%d | failed=%d",
        len(CITIES),
        len(successful_cities),
        len(skipped_cities),
        len(failed_cities),
    )

    if successful_cities:
        logger.info("Successfully loaded cities: %s", successful_cities)

    if skipped_cities:
        logger.info("Cities with no new data: %s", skipped_cities)

    if failed_cities:
        logger.error("Failed cities: %s", failed_cities)
        logger.error(
            "Weather ingestion completed with failures."
        )
        return 1

    logger.info("Weather ingestion completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
