from dataclasses import dataclass
from datetime import UTC, date, datetime


@dataclass
class Location:
    city_name: str | None
    country_code: str | None
    lat: float
    lon: float
    timezone: str | None
    timezone_offset: int | None


@dataclass
class WeatherCondition:
    openweather_weather_id: int
    main: str
    description: str
    icon: str | None


@dataclass
class CurrentWeather:
    location: Location
    weather_condition: WeatherCondition

    observed_at: datetime
    sunrise_at: datetime | None
    sunset_at: datetime | None

    temp: float
    feels_like: float | None
    pressure: int | None
    humidity: int | None
    dew_point: float | None
    uvi: float | None
    clouds: int | None
    visibility: int | None
    wind_speed: float | None
    wind_deg: int | None
    wind_gust: float | None
    rain_1h: float | None
    snow_1h: float | None


@dataclass
class DailyForecast:
    location: Location
    weather_condition: WeatherCondition

    forecast_date: date
    retrieved_at: datetime

    sunrise_at: datetime | None
    sunset_at: datetime | None
    moonrise_at: datetime | None
    moonset_at: datetime | None
    moonphase: float | None

    temp_day: float | None
    temp_min: float | None
    temp_max: float | None
    temp_night: float | None
    temp_evening: float | None
    temp_morning: float | None
    feels_like_day: float | None
    feels_like_night: float | None

    pressure: int | None
    humidity: int | None
    dew_point: float | None
    wind_speed: float | None
    wind_deg: int | None
    wind_gust: float | None
    clouds: int | None
    pop: float | None
    rain: float | None
    snow: float | None
    uvi: float | None


@dataclass
class HourlyForecast:
    location: Location
    weather_condition: WeatherCondition

    forecast_for: datetime
    retrieved_at: datetime

    temp: float
    feels_like: float | None
    pressure: int | None
    humidity: int | None
    dew_point: float | None
    uvi: float | None
    clouds: int | None
    visibility: int | None
    pop: float | None
    wind_speed: float | None
    wind_deg: int | None
    wind_gust: float | None
    rain_1h: float | None
    snow_1h: float | None


@dataclass
class MinutelyForecast:
    location: Location

    forecast_for: datetime
    retrieved_at: datetime
    precipitation: float


@dataclass
class AirPollution:
    location: Location

    observed_at: datetime
    aqi: int
    co: float | None
    no: float | None
    no2: float | None
    o3: float | None
    so2: float | None
    pm2_5: float | None
    pm10: float | None
    nh3: float | None


@dataclass
class WeatherAlert:
    location: Location

    sender_name: str | None
    event: str
    start_at: datetime
    end_at: datetime
    description: str | None
    tags: str | None


def ts(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, UTC)


def parse_location(
    data: dict,
    city_name: str | None = None,
    country_code: str | None = None,
) -> Location:
    return Location(
        city_name=city_name,
        country_code=country_code,
        lat=data["lat"],
        lon=data["lon"],
        timezone=data.get("timezone"),
        timezone_offset=data.get("timezone_offset"),
    )


def parse_weather_condition(weather: dict) -> WeatherCondition:
    return WeatherCondition(
        openweather_weather_id=weather["id"],
        main=weather["main"],
        description=weather["description"],
        icon=weather.get("icon"),
    )


def parse_current_weather(
    data: dict,
    city_name: str | None = None,
    country_code: str | None = None,
) -> CurrentWeather:
    current = data["current"]

    return CurrentWeather(
        location=parse_location(data, city_name, country_code),
        weather_condition=parse_weather_condition(current["weather"][0]),

        observed_at=ts(current["dt"]),
        sunrise_at=ts(current.get("sunrise")),
        sunset_at=ts(current.get("sunset")),

        temp=current["temp"],
        feels_like=current.get("feels_like"),
        pressure=current.get("pressure"),
        humidity=current.get("humidity"),
        dew_point=current.get("dew_point"),
        uvi=current.get("uvi"),
        clouds=current.get("clouds"),
        visibility=current.get("visibility"),
        wind_speed=current.get("wind_speed"),
        wind_deg=current.get("wind_deg"),
        wind_gust=current.get("wind_gust"),
        rain_1h=current.get("rain", {}).get("1h"),
        snow_1h=current.get("snow", {}).get("1h"),
    )


def parse_daily_forecast(
    day: dict,
    location: Location,
    retrieved_at: datetime | None = None,
) -> DailyForecast:
    return DailyForecast(
        location=location,
        weather_condition=parse_weather_condition(day["weather"][0]),

        forecast_date=ts(day["dt"]).date(),
        retrieved_at=retrieved_at or datetime.now(UTC),

        sunrise_at=ts(day.get("sunrise")),
        sunset_at=ts(day.get("sunset")),
        moonrise_at=ts(day.get("moonrise")),
        moonset_at=ts(day.get("moonset")),
        moonphase=day.get("moon_phase"),

        temp_day=day.get("temp", {}).get("day"),
        temp_min=day.get("temp", {}).get("min"),
        temp_max=day.get("temp", {}).get("max"),
        temp_night=day.get("temp", {}).get("night"),
        temp_evening=day.get("temp", {}).get("eve"),
        temp_morning=day.get("temp", {}).get("morn"),
        feels_like_day=day.get("feels_like", {}).get("day"),
        feels_like_night=day.get("feels_like", {}).get("night"),

        pressure=day.get("pressure"),
        humidity=day.get("humidity"),
        dew_point=day.get("dew_point"),
        wind_speed=day.get("wind_speed"),
        wind_deg=day.get("wind_deg"),
        wind_gust=day.get("wind_gust"),
        clouds=day.get("clouds"),
        pop=day.get("pop"),
        rain=day.get("rain"),
        snow=day.get("snow"),
        uvi=day.get("uvi"),
    )


def parse_hourly_forecast(
    hour: dict,
    location: Location,
    retrieved_at: datetime | None = None,
) -> HourlyForecast:
    return HourlyForecast(
        location=location,
        weather_condition=parse_weather_condition(hour["weather"][0]),

        forecast_for=ts(hour["dt"]),
        retrieved_at=retrieved_at or datetime.now(UTC),

        temp=hour["temp"],
        feels_like=hour.get("feels_like"),
        pressure=hour.get("pressure"),
        humidity=hour.get("humidity"),
        dew_point=hour.get("dew_point"),
        uvi=hour.get("uvi"),
        clouds=hour.get("clouds"),
        visibility=hour.get("visibility"),
        pop=hour.get("pop"),
        wind_speed=hour.get("wind_speed"),
        wind_deg=hour.get("wind_deg"),
        wind_gust=hour.get("wind_gust"),
        rain_1h=hour.get("rain", {}).get("1h"),
        snow_1h=hour.get("snow", {}).get("1h"),
    )


def parse_minutely_forecast(
    minute: dict,
    location: Location,
    retrieved_at: datetime | None = None,
) -> MinutelyForecast:
    return MinutelyForecast(
        location=location,
        forecast_for=ts(minute["dt"]),
        retrieved_at=retrieved_at or datetime.now(UTC),
        precipitation=minute["precipitation"],
    )


def parse_air_pollution(
    data: dict,
    location: Location,
) -> AirPollution:
    item = data["list"][0]
    components = item["components"]

    return AirPollution(
        location=location,

        observed_at=ts(item["dt"]),
        aqi=item["main"]["aqi"],

        co=components.get("co"),
        no=components.get("no"),
        no2=components.get("no2"),
        o3=components.get("o3"),
        so2=components.get("so2"),
        pm2_5=components.get("pm2_5"),
        pm10=components.get("pm10"),
        nh3=components.get("nh3"),
    )


def parse_weather_alert(
    alert: dict,
    location: Location,
) -> WeatherAlert:
    return WeatherAlert(
        location=location,

        sender_name=alert.get("sender_name"),
        event=alert["event"],
        start_at=ts(alert["start"]),
        end_at=ts(alert["end"]),
        description=alert.get("description"),
        tags=",".join(alert.get("tags", [])) if alert.get("tags") else None,
    )