import polars as pl

from config.openweather_columns import COLUMNS

from common.logging import get_logger

logger = get_logger(__name__, "weather_transform.log")


class WeatherTransform:


    def __init__(self, data: dict | list[dict], source: str):

        self.data = data
        self.source = source
        self.COLUMNS = COLUMNS


    @staticmethod
    def _coalesce(*values):
        """Return the first value that is not None or an empty string."""

        for value in values:
            if value is not None and value != "":
                return value
        return None


    @staticmethod 
    def _as_dict(value) -> dict: 
        """Return a dictionary or an empty dictionary.""" 
        
        return value if isinstance(value, dict) else {}


    def _as_records(self) -> list[dict]:
        """Normalize payloads to a list of record dictionaries."""

        if isinstance(self.data, list):
            if not all(isinstance(item, dict) for item in self.data):
                raise TypeError("Every item in the weather payload must be a dictionary.")
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
        """Transform saved OpenWeather JSON records.""" 
        
        return self.transform_openweather()


    def transform_openweather(self) -> pl.DataFrame:

        """Transform OpenWeather data into a Polars DataFrame."""

        try:
            records = []

            for item in self._as_records():

                coord = item.get("coord") if isinstance(item.get("coord"), dict) else {}
                main = item.get("main") if isinstance(item.get("main"), dict) else {}
                wind = item.get("wind") if isinstance(item.get("wind"), dict) else {}
                rain = item.get("rain") if isinstance(item.get("rain"), dict) else {}
                clouds = item.get("clouds") if isinstance(item.get("clouds"), dict) else {}
                sys_data = item.get("sys") if isinstance(item.get("sys"), dict) else {}

                weather = item.get("weather") if isinstance(item.get("weather"), list) else []
                first_weather = weather[0] if weather else {}

                records.append({
                    "city": self._coalesce(item.get("city"), item.get("name")),
                    "city_id": item.get("id"),
                    "latitude": self._coalesce(item.get("latitude"), coord.get("lat"), item.get("lat")),
                    "longitude": self._coalesce(item.get("longitude"), coord.get("lon"), item.get("lon")),
                    "country": sys_data.get("country"),
                    "timezone": item.get("timezone"),
                    "base": item.get("base"),

                    "weather_id": first_weather.get("id"),
                    "weather_main": first_weather.get("main"),
                    "weather_description": self._coalesce(
                        item.get("weather_description"), first_weather.get("description")
                    ),
                    "weather_icon": first_weather.get("icon"),

                    "temperature": self._coalesce(item.get("temperature"), main.get("temp"), item.get("temp")),
                    "feels_like": main.get("feels_like"),
                    "temp_min": main.get("temp_min"),
                    "temp_max": main.get("temp_max"),
                    "pressure": self._coalesce(item.get("pressure"), main.get("pressure")),
                    "humidity": self._coalesce(item.get("humidity"), main.get("humidity")),
                    "sea_level": main.get("sea_level"),
                    "ground_level": main.get("grnd_level"),

                    "visibility": item.get("visibility"),
                    "wind_speed": self._coalesce(item.get("wind_speed"), wind.get("speed")),
                    "wind_direction": wind.get("deg"),
                    "wind_gust": wind.get("gust"),

                    "rain_1h": rain.get("1h"),
                    "cloudiness": clouds.get("all"),

                    "observation_time": item.get("dt"),
                    "sunrise": sys_data.get("sunrise"),
                    "sunset": sys_data.get("sunset"),
                    "cod": item.get("cod"),
                })

            if not records: 
                return pl.DataFrame(schema=COLUMNS)

            df = pl.DataFrame(records, schema=COLUMNS, strict=False)
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