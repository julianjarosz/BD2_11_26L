"""API module for fetching and handling OpenWeather data."""

from scripts.api.api_data_struct import (
    Clouds,
    Coordinates,
    MainWeather,
    OpenWeatherData,
    SystemInfo,
    WeatherCondition,
    Wind,
)
from scripts.api.weather_api_fetch import (
    DEFAULT_CITY,
    OpenWeatherFetchManager,
    OPENWEATHER_BASE_URL,
)

__all__ = [
    "DEFAULT_CITY",
    "Clouds",
    "Coordinates",
    "MainWeather",
    "OpenWeatherData",
    "OpenWeatherFetchManager",
    "OPENWEATHER_BASE_URL",
    "SystemInfo",
    "WeatherCondition",
    "Wind",
]
