from scripts.api.openweather_manager import DEFAULT_CITY_NAME, OpenWeatherManager
from scripts.errors.pipeline_errors import OpenWeatherApiSourceError
from scripts.pipeline.source import Row


class OpenWeatherApiSource:
    """Extract mapped OpenWeather rows for the ELT pipeline.

    The source name is used by ``LoadStep.source_name`` to connect configured
    load steps to this source.
    """

    def __init__(
        self,
        name: str,
        manager: OpenWeatherManager | None = None,
    ) -> None:
        """Create an OpenWeather API source.

        Args:
            name: Source identifier referenced by pipeline load steps.
            manager: Optional OpenWeather manager. When omitted, a manager is
                created for the requested resource/city during extraction.
        """
        self.name: str = name
        self.manager = manager

    def extract(self, resource_name: str) -> list[Row]:
        """Fetch one flattened OpenWeather row.

        Args:
            resource_name: City label for the row.

        Returns:
            A one-row list containing the mapped data buffer row.

        Raises:
            OpenWeatherApiSourceError: If the API request or row conversion
            fails.
        """
        city_name = resource_name or DEFAULT_CITY_NAME
        try:
            manager = self.manager or OpenWeatherManager(city_name=city_name)
            return [manager.get_data()]
        except Exception as exc:
            raise OpenWeatherApiSourceError(
                f"Failed to extract OpenWeather data for city {city_name!r} "
                f"from source {self.name!r}: {exc}"
            ) from exc
