from dataclasses import dataclass
from datetime import datetime, UTC, date
from dataclasses import dataclass


from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass
class AirPollution:
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
class MinutelyForecast:
    forecast_for: datetime
    precipitation: float

@dataclass
class HourlyForecast:

    forecast_for: datetime

    temp: float

    feels_like: float

    pressure: int

    humidity: int

    dew_point: float

    uvi: float

    clouds: int

    visibility: int

    pop: float

    wind_speed: float

    wind_deg: int

    wind_gust: float | None

    rain_1h: float | None

    snow_1h: float | None

    weather_id: int

    weather_main: str

    weather_description: str

    weather_icon: str

@dataclass
class CurrentWeather:
    lat: float
    lon: float
    timezone: str
    timezone_offset: int

    observed_at: datetime
    sunrise_at: datetime
    sunset_at: datetime

    temp: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float
    uvi: float
    clouds: int
    visibility: int
    wind_speed: float
    wind_deg: int

    weather_id: int
    weather_main: str
    weather_description: str
    weather_icon: str


@dataclass
class DailyForecast:
    forecast_date: date

    sunrise_at: datetime
    sunset_at: datetime

    moonrise_at: datetime
    moonset_at: datetime
    moon_phase: float

    temp_day: float
    temp_min: float
    temp_max: float
    temp_night: float
    temp_evening: float
    temp_morning: float

    feels_like_day: float
    feels_like_night: float
    feels_like_evening: float
    feels_like_morning: float

    pressure: int
    humidity: int
    dew_point: float

    wind_speed: float
    wind_deg: int
    wind_gust: float

    clouds: int
    pop: float
    rain: float | None
    snow: float | None
    uvi: float

    weather_id: int
    weather_main: str
    weather_description: str
    weather_icon: str

    summary: str

@dataclass

class WeatherAlert:
    sender_name: str
    event: str
    start_at: datetime
    end_at: datetime
    description: str
    tags: list[str]

def parse_current_weather(data: dict) -> CurrentWeather:
    current = data["current"]
    weather = current["weather"][0]

    return CurrentWeather(
        lat=data["lat"],
        lon=data["lon"],
        timezone=data["timezone"],
        timezone_offset=data["timezone_offset"],

        observed_at=datetime.fromtimestamp(current["dt"], UTC),
        sunrise_at=datetime.fromtimestamp(current["sunrise"], UTC),
        sunset_at=datetime.fromtimestamp(current["sunset"], UTC),

        temp=current["temp"],
        feels_like=current["feels_like"],
        pressure=current["pressure"],
        humidity=current["humidity"],
        dew_point=current["dew_point"],
        uvi=current["uvi"],
        clouds=current["clouds"],
        visibility=current["visibility"],
        wind_speed=current["wind_speed"],
        wind_deg=current["wind_deg"],

        weather_id=weather["id"],
        weather_main=weather["main"],
        weather_description=weather["description"],
        weather_icon=weather["icon"]
    )

def parse_daily_forecast(day: dict) -> DailyForecast:
    weather = day["weather"][0]

    return DailyForecast(
        forecast_date=datetime.fromtimestamp(
            day["dt"], UTC
        ).date(),

        sunrise_at=datetime.fromtimestamp(
            day["sunrise"], UTC
        ),

        sunset_at=datetime.fromtimestamp(
            day["sunset"], UTC
        ),

        moonrise_at=datetime.fromtimestamp(
            day["moonrise"], UTC
        ),

        moonset_at=datetime.fromtimestamp(
            day["moonset"], UTC
        ),

        moon_phase=day["moon_phase"],

        temp_day=day["temp"]["day"],
        temp_min=day["temp"]["min"],
        temp_max=day["temp"]["max"],
        temp_night=day["temp"]["night"],
        temp_evening=day["temp"]["eve"],
        temp_morning=day["temp"]["morn"],

        feels_like_day=day["feels_like"]["day"],
        feels_like_night=day["feels_like"]["night"],
        feels_like_evening=day["feels_like"]["eve"],
        feels_like_morning=day["feels_like"]["morn"],

        pressure=day["pressure"],
        humidity=day["humidity"],
        dew_point=day["dew_point"],

        wind_speed=day["wind_speed"],
        wind_deg=day["wind_deg"],
        wind_gust=day["wind_gust"],

        clouds=day["clouds"],
        pop=day["pop"],
        rain=day.get("rain"),
        snow=day.get("snow"),
        uvi=day["uvi"],

        weather_id=weather["id"],
        weather_main=weather["main"],
        weather_description=weather["description"],
        weather_icon=weather["icon"],

        summary=day["summary"]
    )

def parse_hourly_forecast(hour: dict) -> HourlyForecast:

    weather = hour["weather"][0]

    return HourlyForecast(

        forecast_for=datetime.fromtimestamp(

            hour["dt"], UTC

        ),

        temp=hour["temp"],

        feels_like=hour["feels_like"],

        pressure=hour["pressure"],

        humidity=hour["humidity"],

        dew_point=hour["dew_point"],

        uvi=hour["uvi"],

        clouds=hour["clouds"],

        visibility=hour["visibility"],

        pop=hour["pop"],

        wind_speed=hour["wind_speed"],

        wind_deg=hour["wind_deg"],

        wind_gust=hour.get("wind_gust"),

        rain_1h=hour.get("rain", {}).get("1h"),

        snow_1h=hour.get("snow", {}).get("1h"),

        weather_id=weather["id"],

        weather_main=weather["main"],

        weather_description=weather["description"],

        weather_icon=weather["icon"]

    )

def parse_minutely_forecast(minute: dict) -> MinutelyForecast:
    return MinutelyForecast(
        forecast_for=datetime.fromtimestamp(
            minute["dt"], UTC
        ),

        precipitation=minute["precipitation"]
    )


def parse_weather_alert(alert: dict) -> WeatherAlert:
    return WeatherAlert(
        sender_name=alert["sender_name"],
        event=alert["event"],

        start_at=datetime.fromtimestamp(
            alert["start"], UTC
        ),

        end_at=datetime.fromtimestamp(
            alert["end"], UTC
        ),

        description=alert["description"],

        tags=alert.get("tags", [])
    )



def parse_air_pollution(data: dict) -> AirPollution:
    item = data["list"][0]

    components = item["components"]

    return AirPollution(
        observed_at=datetime.fromtimestamp(
            item["dt"], UTC
        ),

        aqi=item["main"]["aqi"],

        co=components.get("co"),
        no=components.get("no"),
        no2=components.get("no2"),
        o3=components.get("o3"),
        so2=components.get("so2"),
        pm2_5=components.get("pm2_5"),
        pm10=components.get("pm10"),
        nh3=components.get("nh3")
    )