from pipeline.ingestion.extract_api import extract_openweather_data, extract_weatherapi_data
from pipeline.ingestion.save_json import save_json
from pipeline.validation.weather_validator import WeatherValidator
from pipeline.transformation.weather_transform import WeatherTransform
from pipeline.loaded.load_postresql import load_postgresql
from pipeline.loaded.save_parquet import save_parquet

from common.logging import get_logger
from config.cities import CITIES

logger = get_logger(__name__, "main.log")


def slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def main():
    try:
        
        """Extract, validate, transform, and optionally store weather data for each city."""

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

                    try:
                        load_postgresql(transformed, f"openweather_{slugify(city)}")

                    except Exception as exc:
                        logger.warning(f"Skipping PostgreSQL load for {city}: {exc}")

                except ValueError as exc:
                    logger.warning(f"OpenWeather data invalid for {city}: {exc}")

            if weatherapi_data:

                try:
                    WeatherValidator.validate_weatherapi(weatherapi_data)
                    save_json(weatherapi_data, city, "weatherapi")

                    transformed = WeatherTransform(weatherapi_data, "weatherapi").transform()
                    save_parquet(transformed, slugify(city), "weatherapi")

                    try:

                        load_postgresql(transformed, f"weatherapi_{slugify(city)}")

                    except Exception as exc:
                        logger.warning(f"Skipping PostgreSQL load for {city}: {exc}")

                except ValueError as exc:
                    logger.warning(f"WeatherAPI data invalid for {city}: {exc}")

        logger.info("Weather extraction pipeline completed successfully.")

    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}")


if __name__ == "__main__":
    main()
