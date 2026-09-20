import json
from pathlib import Path

import polars as pl

from common.logging import get_logger

logger = get_logger(__name__, "weather_transform.log")


class WeatherTransform:

    def __init__(self, data: dict, source: str):

        self.data = data
        self.source = source

    def _as_records(self) -> list[dict]:
        """Normalize payloads to a list of record dictionaries."""

        if isinstance(self.data, list):
            return self.data
        if isinstance(self.data, dict):
            return [self.data]
        raise TypeError(f"Weather payload must be a dict or list of dicts, got {type(self.data)!r}")

    def transform(self) -> pl.DataFrame:

        """Transform the weather data into a Polars DataFrame."""

        if self.source == "openweather":
            return self.transform_openweather()

        if self.source == "weatherapi":
            return self.transform_weatherapi()

        logger.error(f"Unknown data source: {self.source}")
        raise ValueError(f"Unknown data source: {self.source}")

    def transform_openweather(self) -> pl.DataFrame:

        """Transform OpenWeather data into a Polars DataFrame."""

        try:
            records = []
            for item in self._as_records():
                weather = item.get("weather") or [{}]
                first_weather = weather[0] if isinstance(weather, list) and weather else {}
                records.append(
                    {
                        "city": item.get("name"),
                        "latitude": item.get("coord", {}).get("lat"),
                        "longitude": item.get("coord", {}).get("lon"),
                        "temperature": item.get("main", {}).get("temp"),
                        "humidity": item.get("main", {}).get("humidity"),
                        "pressure": item.get("main", {}).get("pressure"),
                        "weather_description": first_weather.get("description"),
                        "wind_speed": item.get("wind", {}).get("speed"),
                    }
                )

            df = pl.DataFrame(records)
            logger.info(f"Transformed OpenWeather data for {len(records)} city record(s)")
            return df

        except Exception as e:
            logger.error(f"Error transforming OpenWeather data: {e}")
            raise

    def transform_weatherapi(self) -> pl.DataFrame:

        """Transform WeatherAPI data into a Polars DataFrame."""

        try:
            records = []
            for item in self._as_records():
                current = item.get("current", {})
                location = item.get("location", {})
                records.append(
                    {
                        "city": location.get("name"),
                        "latitude": location.get("lat"),
                        "longitude": location.get("lon"),
                        "temperature": current.get("temp_c"),
                        "humidity": current.get("humidity"),
                        "pressure": current.get("pressure_mb"),
                        "weather_description": current.get("condition", {}).get("text"),
                        "wind_speed": current.get("wind_kph"),
                    }
                )

            df = pl.DataFrame(records)
            logger.info(f"Transformed {df.height} WeatherAPI record(s)")
            return df

        except Exception as e:
            logger.error(f"Error transforming WeatherAPI data: {e}")
            raise

    def transformation_manager(self) -> dict:

        """Return a dictionary of transformation methods."""

        return {
            "transform_openweather": self.transform_openweather,
            "transform_weatherapi": self.transform_weatherapi,
        }