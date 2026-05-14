"""Async helpers for fetching current weather data from OpenWeather."""

import asyncio
import os
import typing
from scripts.api.api_data_struct import OpenWeatherData
from scripts.utils import fetch_config_value

import requests

OPENWEATHER_BASE_URL: str = fetch_config_value("consts.conf", "openweather.base_url")
API_KEY_ENV_VAR: str = fetch_config_value("consts.conf", "openweather.api_key_env_var")
DEFAULT_TIMEOUT_SECONDS: float = float(fetch_config_value("consts.conf", "openweather.default_timeout_seconds"))
DEFAULT_CITY: str = fetch_config_value("consts.conf", "openweather.default_city")


@typing.final
class OpenWeatherFetchManager:
    """Fetch current weather data for one or more cities.

    The manager wraps a shared ``requests.Session`` for efficient HTTP reuse
    and exposes async methods that offload blocking network calls to threads.
    """

    def __init__(
        self,
        api_key: str,
        init_callbacks: typing.Callable | list[typing.Callable] | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Create a fetch manager.

        Args:
            api_key: OpenWeather API key.
            timeout: Per-request timeout in seconds.
        """
        assert (timeout) > 0.0
        self.api_key: str = api_key
        self.timeout: float = timeout
        self.callbacks: list[typing.Callable] = (
            init_callbacks if isinstance(init_callbacks, list) else [init_callbacks] if init_callbacks else []
        )
        self.session: requests.Session = requests.Session()

    def _fetch_city_data(self, city, **kwargs: dict[str, typing.Any]) -> OpenWeatherData:
        """Fetch OpenWeather API data by provided city or cities"""
        api_response = self.session.get(
            OPENWEATHER_BASE_URL,
            params={"q": city, "appid": self.api_key, **kwargs},
            timeout=self.timeout,
        )
        api_response.raise_for_status()
        return OpenWeatherData.from_api_response(api_response.json())

    async def fetch_city(self, city: str, **kwargs: typing.Any) -> OpenWeatherData:
        """Fetch weather data for one city without blocking the event loop."""
        return await asyncio.to_thread(self._fetch_city_data, city, **kwargs)

    async def fetch_cities(self, cities: typing.Iterable[str], **kwargs: typing.Any) -> list[OpenWeatherData]:
        """Fetch data from many cities without blocking the event loop."""
        tasks: list[typing.Awaitable[OpenWeatherData]] = [self.fetch_city(city, **kwargs) for city in cities]
        results = asyncio.gather(*tasks)
        return await results

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()
