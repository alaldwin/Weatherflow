import polars as pl

from common.logging import get_logger

logger = get_logger(__name__, "weather_transform.log")


class WeatherTransform:

    OPENWEATHER_COLUMNS = [
        "city",
        "latitude",
        "longitude",
        "temperature",
        "humidity",
        "pressure",
        "weather_description",
        "wind_speed",
    ]

    def __init__(self, data: dict, source: str):

        self.data = data
        self.source = source

    @staticmethod
    def _coalesce(*values):
        for value in values:
            if value is not None and value != "":
                return value
        return None

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

        if self.source == "geocoding":
            return self.transform_geocoding()

        logger.error(f"Unknown data source: {self.source}")
        raise ValueError(f"Unknown data source: {self.source}")

    def transform_raw_json(self) -> pl.DataFrame:
        """Transform saved raw JSON records created by save_json()."""

        try:
            records = []
            for item in self._as_records():
                records.append(
                    {
                        "city": self._coalesce(item.get("city"), item.get("name")),
                        "latitude": self._coalesce(item.get("latitude"), item.get("lat")),
                        "longitude": self._coalesce(item.get("longitude"), item.get("lon")),
                        "temperature": self._coalesce(item.get("temperature"), item.get("temp")),
                        "humidity": self._coalesce(item.get("humidity"), item.get("main", {}).get("humidity")),
                        "pressure": self._coalesce(item.get("pressure"), item.get("main", {}).get("pressure")),
                        "weather_description": self._coalesce(
                            item.get("weather_description"),
                            (item.get("weather") or [{}])[0].get("description") if isinstance(item.get("weather"), list) and item.get("weather") else None,
                        ),
                        "wind_speed": self._coalesce(item.get("wind_speed"), item.get("wind", {}).get("speed")),
                    }
                )

            df = pl.DataFrame(records, schema=self.OPENWEATHER_COLUMNS)
            logger.info(f"Transformed raw JSON data for {len(records)} record(s)")
            return df

        except Exception as exc:
            logger.error(f"Error transforming raw JSON data: {exc}")
            raise

    def transform_openweather(self) -> pl.DataFrame:

        """Transform OpenWeather data into a Polars DataFrame."""

        try:
            records = []
            for item in self._as_records():
                coord = item.get("coord") if isinstance(item.get("coord"), dict) else {}
                main = item.get("main") if isinstance(item.get("main"), dict) else {}
                wind = item.get("wind") if isinstance(item.get("wind"), dict) else {}
                weather = item.get("weather") if isinstance(item.get("weather"), list) else []
                first_weather = weather[0] if weather else {}

                if any(key in item for key in ("city", "latitude", "longitude", "temperature", "humidity", "pressure", "weather_description", "wind_speed")):
                    row = {
                        "city": self._coalesce(item.get("city"), item.get("name")),
                        "latitude": self._coalesce(item.get("latitude"), coord.get("lat")),
                        "longitude": self._coalesce(item.get("longitude"), coord.get("lon")),
                        "temperature": self._coalesce(item.get("temperature"), main.get("temp")),
                        "humidity": self._coalesce(item.get("humidity"), main.get("humidity")),
                        "pressure": self._coalesce(item.get("pressure"), main.get("pressure")),
                        "weather_description": self._coalesce(item.get("weather_description"), first_weather.get("description")),
                        "wind_speed": self._coalesce(item.get("wind_speed"), wind.get("speed")),
                    }
                else:
                    row = {
                        "city": item.get("name"),
                        "latitude": coord.get("lat"),
                        "longitude": coord.get("lon"),
                        "temperature": main.get("temp"),
                        "humidity": main.get("humidity"),
                        "pressure": main.get("pressure"),
                        "weather_description": first_weather.get("description"),
                        "wind_speed": wind.get("speed"),
                    }
                records.append(row)

            df = pl.DataFrame(records, schema=self.OPENWEATHER_COLUMNS)
            logger.info(f"Transformed OpenWeather data for {len(records)} city record(s)")
            return df

        except Exception as e:
            logger.error(f"Error transforming OpenWeather data: {e}")
            raise

    def transform_geocoding(self) -> pl.DataFrame:

        """Transform geocoding metadata into a Polars DataFrame."""

        try:
            records = []
            for item in self._as_records():
                records.append(
                    {
                        "city": item.get("name") or item.get("city"),
                        "latitude": item.get("lat") or item.get("latitude"),
                        "longitude": item.get("lon") or item.get("longitude"),
                        "country": item.get("country"),
                        "state": item.get("state"),
                    }
                )

            df = pl.DataFrame(records)
            logger.info(f"Transformed {df.height} geocoding record(s)")
            return df

        except Exception as e:
            logger.error(f"Error transforming geocoding data: {e}")
            raise

    def transformation_manager(self) -> dict:

        """Return a dictionary of transformation methods."""

        return {
            "transform_openweather": self.transform_openweather,
            "transform_geocoding": self.transform_geocoding,
            "transform_raw_json": self.transform_raw_json,
        }