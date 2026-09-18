import json
from pathlib import Path

import polars as pl

from common.logging import get_logger

logger = get_logger(__name__, "weather_transform.log")


class WeatherTransform:

    def __init__(self, data: dict, source: str):

        self.data = data
        self.source = source

    def transform(self) -> pl.DataFrame:

        """Transform the weather data into a Polars DataFrame."""

        if self.source == "openweather":
            return self.transform_openweather()
        elif self.source == "weatherapi":
            return self.transform_weatherapi()
        else:
            logger.error(f"Unknown data source: {self.source}")
            raise ValueError(f"Unknown data source: {self.source}")


    def transform_openweather(self) -> pl.DataFrame:

        """Transform OpenWeather data into a Polars DataFrame."""

        try:

            df = pl.DataFrame(
                {
                    "city": [self.data.get("name")],
                    "latitude": [self.data.get("coord", {}).get("lat")],
                    "longitude": [self.data.get("coord", {}).get("lon")],
                    "temperature": [self.data.get("main", {}).get("temp")],
                    "humidity": [self.data.get("main", {}).get("humidity")],
                    "pressure": [self.data.get("main", {}).get("pressure")],
                    "weather_description": [
                        self.data.get("weather", [{}])[0].get("description")
                    ],
                    "wind_speed": [self.data.get("wind", {}).get("speed")],
                }
            )
            logger.info(f"Transformed OpenWeather data for city: {self.data.get('name')}")

            return df

        except Exception as e:
            logger.error(f"Error transforming OpenWeather data: {e}")
            raise



    def transform_weatherapi(self) -> pl.DataFrame:

        """Transform WeatherAPI data into a Polars DataFrame."""

        try:

            current = self.data.get("current", {})
            df = pl.DataFrame(
                {
                    "city": [self.data.get("location", {}).get("name")],
                    "latitude": [self.data.get("location", {}).get("lat")],
                    "longitude": [self.data.get("location", {}).get("lon")],
                    "temperature": [current.get("temp_c")],
                    "humidity": [current.get("humidity")],
                    "pressure": [current.get("pressure_mb")],
                    "weather_description": [
                        current.get("condition", {}).get("text")
                    ],
                    "wind_speed": [current.get("wind_kph")],
                }
            )
            logger.info(
                "Transformed WeatherAPI data for city: %s",
                self.data.get("location", {}).get("name"),
            )

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