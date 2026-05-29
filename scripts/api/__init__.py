"""API module for fetching and parsing OpenWeather data."""

from scripts.api.api_struct import (
    AirPollution,
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    Location,
    MinutelyForecast,
    OpenWeatherDataParser,
    WeatherAlert,
    WeatherCondition,
)
from scripts.api.openweather_manager import OpenWeatherManager

__all__ = [
    "AirPollution",
    "CurrentWeather",
    "DailyForecast",
    "HourlyForecast",
    "Location",
    "MinutelyForecast",
    "OpenWeatherDataParser",
    "OpenWeatherManager",
    "WeatherAlert",
    "WeatherCondition",
]
