from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WeatherBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    city: str
    country: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    humidity: int | None = Field(default=None, ge=0, le=100)
    cloudiness: int | None = Field(default=None, ge=0, le=100)


class CurrentWeather(WeatherBase):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    temperature: float | None = None
    feels_like: float | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    humidity: int | None = Field(default=None, ge=0, le=100)
    pressure: int | None = None
    visibility: int | None = None
    wind_speed: float | None = None
    wind_direction: int | None = None
    wind_gust: float | None = None
    cloudiness: int | None = Field(default=None, ge=0, le=100)
    weather_main: str | None = None
    weather_description: str | None = None
    weather_icon: str | None = None
    observation_time: datetime | None = None
    sunrise: datetime | int | float | None = None
    sunset: datetime | int | float | None = None


class CurrentWeatherListResponse(BaseModel):
    count: int
    limit: int
    offset: int
    has_more: bool
    data: list[CurrentWeather]


class DailyWeather(WeatherBase):
    observation_date: date
    avg_temperature: float | None = None
    min_temperature: float | None = None
    max_temperature: float | None = None
    avg_feels_like: float | None = None
    avg_humidity: float | None = None
    avg_pressure: float | None = None
    avg_wind_speed: float | None = None
    avg_cloudiness: float | None = None
    observation_count: int | None = None


class DateFilters(BaseModel):
    city: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be on or before end_date")

        return self


class DailyWeatherResponse(BaseModel):
    count: int
    filters: DateFilters
    data: list[DailyWeather]


class WeatherTrend(WeatherBase):
    observation_date: date
    avg_temperature: float | None = None
    previous_avg_temperature: float | None = None
    temperature_change: float | None = None
    avg_humidity: float | None = None
    previous_avg_humidity: float | None = None
    humidity_change: float | None = None


class WeatherTrendsResponse(BaseModel):
    count: int
    filters: DateFilters
    data: list[WeatherTrend]


class CityComparison(WeatherBase):
    temperature: float | None = None
    feels_like: float | None = None
    humidity: int | None = Field(default=None, ge=0, le=100)
    pressure: int | None = None
    wind_speed: float | None = None
    cloudiness: int | None = Field(default=None, ge=0, le=100)
    weather_main: str | None = None
    weather_description: str | None = None
    observation_time: datetime | None = None
    temperature_rank: float | None = None
    average_city_temperature: float | None = None
    difference_from_average: float | None = None


class SortOptions(BaseModel):
    sort_by: Literal["temperature", "humidity", "wind_speed", "city"]
    order: Literal["asc", "desc"]


class CityComparisonResponse(BaseModel):
    count: int
    limit: int
    offset: int
    has_more: bool
    sort: SortOptions
    data: list[CityComparison]
