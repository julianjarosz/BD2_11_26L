"""OpenWeather API-backed source for the ELT pipeline."""

import asyncio

from scripts.api.weather_api_fetch import (
    API_KEY_ENV_VAR,
    DEFAULT_CITY,
    OpenWeatherFetchManager,
)
from scripts.errors.pipeline_errors import OpenWeatherApiSourceError
from scripts.pipeline.source import Row
from scripts.utils import load_api_key


class OpenWeatherApiSource:
    """Extract current weather rows from the OpenWeather API.

    The source name is used by ``LoadStep.source_name`` to connect configured
    load steps to this source. ``resource_name`` values passed to
    :meth:`extract` are treated as city names. When ``resource_name`` is empty,
    the configured default city is used.
    """

    def __init__(
        self,
        name: str,
        fetch_manager: OpenWeatherFetchManager | None = None,
    ) -> None:
        """Create an OpenWeather API source.

        Args:
            name: Source identifier referenced by pipeline load steps.
            fetch_manager: Optional fetch manager. When omitted, a manager is
                created from the configured OpenWeather API key environment
                variable.
        """
        self.name: str = name
        self.fetch_manager: OpenWeatherFetchManager = fetch_manager or OpenWeatherFetchManager(
            load_api_key(API_KEY_ENV_VAR)
        )

    def extract(self, resource_name: str) -> list[Row]:
        """Fetch current weather for one city.

        Args:
            resource_name: City name to fetch. Uses the configured default city
                when empty.

        Returns:
            A one-row list containing the OpenWeather data buffer row.

        Raises:
            OpenWeatherApiSourceError: If the API request or row conversion
            fails.
        """
        city = resource_name or DEFAULT_CITY
        try:
            weather_data = asyncio.run(
                self.fetch_manager.fetch_city(city, units="metric")
            )
            return [weather_data.to_data_buffer_row()]
        except Exception as exc:
            raise OpenWeatherApiSourceError(
                f"Failed to extract OpenWeather data for city {city!r} "
                f"from source {self.name!r}: {exc}"
            ) from exc

    def close(self) -> None:
        """Close the underlying OpenWeather fetch manager session."""
        self.fetch_manager.close()
