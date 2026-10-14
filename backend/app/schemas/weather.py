from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class WeatherBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    city: str
    country: str | None = None


class CurrentWeather(WeatherBase):
    latitude: float | None = None
    longitude: float | None = None
    temperature: float | None = None
    feels_like: float | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    humidity: int | None = None
    pressure: int | None = None
    visibility: int | None = None
    wind_speed: float | None = None
    wind_direction: int | None = None
    wind_gust: float | None = None
    cloudiness: int | None = None
    weather_main: str | None = None
    weather_description: str | None = None
    weather_icon: str | None = None
    observation_time: datetime | None = None
    sunrise: datetime | int | float | None = None
    sunset: datetime | int | float | None = None


class CurrentWeatherListResponse(BaseModel):
    count: int
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
    humidity: int | None = None
    pressure: int | None = None
    wind_speed: float | None = None
    cloudiness: int | None = None
    weather_main: str | None = None
    weather_description: str | None = None
    observation_time: datetime | None = None
    temperature_rank: int | None = None
    average_city_temperature: float | None = None
    difference_from_average: float | None = None


class SortOptions(BaseModel):
    sort_by: str
    order: str


class CityComparisonResponse(BaseModel):
    count: int
    sort: SortOptions
    data: list[CityComparison]
