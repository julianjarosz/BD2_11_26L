"""Async helpers for fetching current weather data from OpenWeather."""

import asyncio
import os
import typing
from configparser import ConfigParser
from pathlib import Path
from scripts.api.api_data_struct import OpenWeatherData

import requests

CONFIG_PATH = Path(__file__).with_name("api.conf")
EXAMPLE_CONFIG_PATH = Path(__file__).with_name("api.conf.example")
API_KEY_ENV_VAR = "OPENWEATHER_API_KEY"


def _load_config() -> ConfigParser:
    """Load project configuration from the local or example config file."""
    parser = ConfigParser()
    parser.read([str(EXAMPLE_CONFIG_PATH), str(CONFIG_PATH)])
    return parser


def _load_base_url() -> str:
    """Load the OpenWeather base URL from configuration."""
    parser = _load_config()
    return parser["openweather"]["base_url"]


def _load_api_key() -> str:
    """Load the OpenWeather API key from local config or environment."""
    if CONFIG_PATH.exists():
        parser = ConfigParser()
        parser.read(CONFIG_PATH)
        api_key = parser["openweather"].get("api_key", "").strip()
        if api_key:
            return api_key

    api_key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if api_key:
        return api_key

    raise ValueError("OpenWeather API key not found in scripts/api.conf or " f"environment variable {API_KEY_ENV_VAR}.")


OPENWEATHER_BASE_URL: str = _load_base_url()


@typing.final
class OpenWeatherFetchManager:
    """Fetch current weather data for one or more cities.

    The manager wraps a shared ``requests.Session`` for efficient HTTP reuse
    and exposes async methods that offload blocking network calls to threads.
    """

    def __init__(
        self,
        api_key: str,
        init_callbacks: typing.Callable | list[typing.Callable],
        timeout: float = 10.0,
    ) -> None:
        """Create a fetch manager.

        Args:
            api_key: OpenWeather API key.
            timeout: Per-request timeout in seconds.
        """
        assert (timeout) > 0.0
        self.api_key: str = api_key
        self.timeout: float = timeout
        self.callbacks: list[typing.Callable] = init_callbacks if isinstance(init_callbacks, list) else [init_callbacks]
        self.session: requests.Session = requests.Session()

    def _fetch_city_data(self, city, **kwargs: dict[str, typing.Any]) -> OpenWeatherData:
        """Fetch OpenWeather API data by provided city or cities"""
        api_response = self.session.get(
            OPENWEATHER_BASE_URL,
            params={"q": city, "appid": self.api_key, **kwargs},
            timeout=self.timeout,
        )
        api_response.raise_for_status()
        return api_response.json()

    async def fetch_city(self, cities: str) -> OpenWeatherData:
        """Fetch weather data for one city without blocking the event loop."""
        return await asyncio.to_thread(self._fetch_city_data, cities)

    async def fetch_cities(self, cities: typing.Itterable[str]) -> typing.Itterable[OpenWeatherData]:
        """Fetch data from many cities without blocking the event loop."""
        tasks: list[OpenWeatherData] = [self.fetch_city(city) for city in cities]
        results = asyncio.gather(*tasks)
        return results

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()
