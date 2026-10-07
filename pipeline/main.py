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
    """Run the complete weather pipeline."""

    logger.info("Starting Weather Ingestion...")

    for city, coordinates in CITIES.items():
        latitude = coordinates["latitude"]
        longitude = coordinates["longitude"]

        logger.info("Processing city: %s", city)

        try:
            weather_data = extract_openweather_data(latitude, longitude, city)
            if not weather_data:
                logger.warning("No weather data returned for %s", city)
                continue

            geocoding_data = extract_geocoding_data(latitude, longitude, city)
            if geocoding_data:
                logger.info("Geocoding extracted for %s", city)
                geocoding_df = WeatherTransform(geocoding_data, "geocoding").transform()
                if not geocoding_df.is_empty():
                    geocoding_table = _table_name("geocoding", city)
                    load_postgresql(geocoding_df, geocoding_table, if_exists="replace")
                    logger.info("Geocoding loaded for %s into %s", city, geocoding_table)
            else:
                logger.warning("No geocoding data returned for %s", city)

            observation_time = weather_data.get("dt")
            if observation_time is None:
                logger.warning("Missing observation timestamp for %s; skipping incremental check", city)
                continue

            if not is_new_data(source="openweather", location=city, observation_time=observation_time):
                logger.info("No new weather data for %s. Skipping.", city)
                continue

            output_file = save_json(data=weather_data, city=city, source="openweather")
            if output_file is None:
                logger.warning("Raw JSON was not saved for %s; skipping downstream processing", city)
                continue

            logger.info("Raw JSON saved for %s: %s", city, output_file)

            weather_df = WeatherTransform(weather_data, "openweather").transform()
            if weather_df.is_empty():
                logger.warning("Transformation produced no data for %s.", city)
                continue

            logger.info("Weather data transformed for %s.", city)

            parquet_file = save_parquet(weather_df, city, "openweather")
            if parquet_file is None:
                logger.warning("Parquet file was not saved for %s", city)
                continue

            logger.info("Parquet saved for %s: %s", city, parquet_file)

            table_name = _table_name("openweather", city)
            loaded_rows = load_postgresql(parquet_file, table_name=table_name, if_exists="replace")
            logger.info("Loaded %d row(s) for %s into %s.", loaded_rows, city, table_name)

            update_state(source="openweather", location=city, observation_time=observation_time)
            logger.info("Checkpoint updated for %s.", city)

        except Exception:
            logger.exception("Failed to process city: %s", city)
            continue

    logger.info("Weather ingestion completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main()) 