"""Async helpers for fetching current weather data from OpenWeather."""

import asyncio
from configparser import ConfigParser
from pathlib import Path
from typing import Iterable, final

import requests


CONFIG_PATH = Path(__file__).with_name("api.conf")


def _load_base_url() -> str:
    """Load the OpenWeather base URL from the local config file."""
    parser = ConfigParser()
    parser.read(CONFIG_PATH)
    return parser["openweather"]["base_url"]


OPENWEATHER_BASE_URL: str = _load_base_url()


@final
class OpenWeatherFetchManager:
    """Fetch current weather data for one or more cities.

    The manager wraps a shared ``requests.Session`` for efficient HTTP reuse
    and exposes async methods that offload blocking network calls to threads.
    """

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        """Create a fetch manager.

        Args:
            api_key: OpenWeather API key.
            timeout: Per-request timeout in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def _fetch(self, city: str) -> dict:
        """Fetch weather data for a single city synchronously."""
        response = self.session.get(
            OPENWEATHER_BASE_URL,
            params={"q": city, "appid": self.api_key},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    async def fetch_city(self, city: str) -> dict:
        """Fetch weather data for one city without blocking the event loop."""
        return await asyncio.to_thread(self._fetch, city)

    async def fetch_cities(self, cities: Iterable[str]) -> list[dict]:
        """Fetch weather data for multiple cities concurrently."""
        tasks = [self.fetch_city(city) for city in cities]
        return await asyncio.gather(*tasks)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()
