"""Typed data structures for OpenWeather current weather responses.

This module mirrors the nested JSON returned by the current weather endpoint
and provides helpers to convert between raw API payloads and dataclass
instances used in the project.
"""

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Coordinates:
    """Geographic coordinates."""

    lon: float
    lat: float


@dataclass(slots=True)
class WeatherCondition:
    """Single weather condition entry."""

    id: int
    main: str
    description: str
    icon: str


@dataclass(slots=True)
class MainWeather:
    """Main temperature and pressure data."""

    temp: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int
    sea_level: int | None
    grnd_level: int | None


@dataclass(slots=True)
class Wind:
    """Wind data."""

    speed: float
    deg: int | None


@dataclass(slots=True)
class Clouds:
    """Cloudiness data."""

    all: int


@dataclass(slots=True)
class SystemInfo:
    """System metadata from OpenWeather."""

    type: int | None
    id: int | None
    country: str
    sunrise: int
    sunset: int


@dataclass(slots=True)
class OpenWeatherData:
    """Typed representation of the current weather API response.

    The structure follows the OpenWeather response shape closely, which makes
    it easy to move between raw JSON data and typed Python objects.
    """

    coord: Coordinates
    weather: list[WeatherCondition]
    base: str
    main: MainWeather
    visibility: int
    wind: Wind
    clouds: Clouds
    dt: int
    sys: SystemInfo
    timezone: int
    id: int
    name: str
    cod: int

    @classmethod
    def from_api_response(cls, payload: dict) -> "OpenWeatherData":
        """Create the dataclass tree from a raw OpenWeather API response."""
        return cls(
            coord=Coordinates(
                lon=payload["coord"]["lon"],
                lat=payload["coord"]["lat"],
            ),
            weather=[
                WeatherCondition(
                    id=item["id"],
                    main=item["main"],
                    description=item["description"],
                    icon=item["icon"],
                )
                for item in payload["weather"]
            ],
            base=payload["base"],
            main=MainWeather(
                temp=payload["main"]["temp"],
                feels_like=payload["main"]["feels_like"],
                temp_min=payload["main"]["temp_min"],
                temp_max=payload["main"]["temp_max"],
                pressure=payload["main"]["pressure"],
                humidity=payload["main"]["humidity"],
                sea_level=payload["main"].get("sea_level"),
                grnd_level=payload["main"].get("grnd_level"),
            ),
            visibility=payload["visibility"],
            wind=Wind(
                speed=payload["wind"]["speed"],
                deg=payload["wind"].get("deg"),
            ),
            clouds=Clouds(all=payload["clouds"]["all"]),
            dt=payload["dt"],
            sys=SystemInfo(
                type=payload["sys"].get("type"),
                id=payload["sys"].get("id"),
                country=payload["sys"]["country"],
                sunrise=payload["sys"]["sunrise"],
                sunset=payload["sys"]["sunset"],
            ),
            timezone=payload["timezone"],
            id=payload["id"],
            name=payload["name"],
            cod=payload["cod"],
        )

    def to_dict(self) -> dict:
        """Convert the dataclass tree into a plain dictionary."""
        return asdict(self)
