"""Typed data structures for OpenWeather current weather responses.

This module mirrors the nested JSON returned by the current weather endpoint
and provides helpers to convert between raw API payloads and dataclass
instances used in the project.
"""

import datetime
from dataclasses import asdict, dataclass


def _utc_datetime_from_timestamp(timestamp: int | None) -> datetime.datetime | None:
    if timestamp is None:
        return None
    return datetime.datetime.fromtimestamp(timestamp, datetime.UTC)


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
    gust: float | None


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
    rain: dict[str, float] | None
    snow: dict[str, float] | None
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
                gust=payload["wind"].get("gust"),
            ),
            clouds=Clouds(all=payload["clouds"]["all"]),
            rain=payload.get("rain"),
            snow=payload.get("snow"),
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

    def to_data_buffer_row(self) -> dict[str, object]:
        """Convert current OpenWeather data into one operational ``data_buffer`` row."""
        observed_at = _utc_datetime_from_timestamp(self.dt)
        if observed_at is None:
            observed_at = datetime.datetime.now(datetime.UTC)
        retrieved_at = datetime.datetime.now(datetime.UTC)
        condition = self.weather[0] if self.weather else None
        condition_id = condition.id if condition is not None else 0
        current_weather_id = int(f"{self.dt}{self.id}")
        location_id = self.id
        rain_1h = self.rain.get("1h") if self.rain else None
        snow_1h = self.snow.get("1h") if self.snow else None
        sunrise_at = _utc_datetime_from_timestamp(self.sys.sunrise)
        sunset_at = _utc_datetime_from_timestamp(self.sys.sunset)
        return {
            "current_weather_id": current_weather_id,
            "observed_at": observed_at,
            "sunrise_at": sunrise_at,
            "sunset_at": sunset_at,
            "temp": self.main.temp,
            "feels_like": self.main.feels_like,
            "pressure": self.main.pressure,
            "humidity": self.main.humidity,
            "dew_point": None,
            "uvi": None,
            "clouds": self.clouds.all,
            "visibility": self.visibility,
            "wind_speed": self.wind.speed,
            "wind_deg": self.wind.deg,
            "wind_gust": self.wind.gust,
            "rain_1h": rain_1h,
            "snow_1h": snow_1h,
            "location_id1": location_id,
            "condition_id": condition_id,
            "condition_id_1": condition_id,
            "openweather_weather_id": condition_id,
            "main": condition.main if condition is not None else "Unknown",
            "description": condition.description if condition is not None else "unknown",
            "icon": condition.icon if condition is not None else None,
            "daily_forecast_id": current_weather_id,
            "forecast_date": observed_at.date(),
            "retrieved_at": retrieved_at,
            "sunrise_at_1": sunrise_at,
            "sunset_at_1": sunset_at,
            "moonrise_at": None,
            "moonset_at": None,
            "moonphase": None,
            "temp_day": self.main.temp,
            "temp_min": self.main.temp_min,
            "temp_max": self.main.temp_max,
            "temp_night": None,
            "temp_evening": None,
            "temp_morning": None,
            "feels_like_day": self.main.feels_like,
            "feels_like_night": None,
            "pressure_1": self.main.pressure,
            "humidity_1": self.main.humidity,
            "dew_point_1": None,
            "wind_speed_1": self.wind.speed,
            "wind_deg_1": self.wind.deg,
            "wind_gust_1": self.wind.gust,
            "clouds_1": self.clouds.all,
            "pop": None,
            "rain": rain_1h,
            "snow": snow_1h,
            "uvi_1": None,
            "location_id": location_id,
            "condition_id_2": condition_id,
            "air_pollution_id": current_weather_id,
            "observed_at_1": observed_at,
            "aqi": 1,
            "co": None,
            "no": None,
            "no2": None,
            "o3": None,
            "so2": None,
            "pm2_5": None,
            "pm10": None,
            "location_id_2": location_id,
            "minutely_forecast_id": current_weather_id,
            "forecast_for": observed_at,
            "retrieved_at_1": retrieved_at,
            "precipitation": None,
            "location_id_3": location_id,
            "hourly_forecast_id": current_weather_id,
            "forecast_for_1": observed_at,
            "retrieved_at_2": retrieved_at,
            "temp_7": self.main.temp,
            "feels_like_3": self.main.feels_like,
            "pressure_2": self.main.pressure,
            "humidity_2": self.main.humidity,
            "dew_point_2": None,
            "uvi_2": None,
            "clouds_2": self.clouds.all,
            "visibility_1": self.visibility,
            "pop_1": None,
            "wind_speed_2": self.wind.speed,
            "wind_deg_2": self.wind.deg,
            "wind_gust_2": self.wind.gust,
            "rain_1h_1": rain_1h,
            "snow_1h_1": snow_1h,
            "location_id_4": location_id,
            "condition_id_3": condition_id,
            "location_id_5": location_id,
            "city_name": self.name,
            "country_code": self.sys.country,
            "lat": self.coord.lat,
            "lon": self.coord.lon,
            "timezone": None,
            "timezone_offset": self.timezone,
        }
