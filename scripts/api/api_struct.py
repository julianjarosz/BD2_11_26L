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


class OpenWeatherDataParser:
    def parse_location(
        self,
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

    def parse_weather_condition(self, weather: dict) -> WeatherCondition:
        return WeatherCondition(
            openweather_weather_id=weather["id"],
            main=weather["main"],
            description=weather["description"],
            icon=weather.get("icon"),
        )

    def parse_current_weather(
        self,
        data: dict,
        city_name: str | None = None,
        country_code: str | None = None,
    ) -> CurrentWeather:
        current = data["current"]

        return CurrentWeather(
            location=self.parse_location(data, city_name, country_code),
            weather_condition=self.parse_weather_condition(current["weather"][0]),
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
        self,
        day: dict,
        location: Location,
        retrieved_at: datetime | None = None,
    ) -> DailyForecast:
        return DailyForecast(
            location=location,
            weather_condition=self.parse_weather_condition(day["weather"][0]),
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
        self,
        hour: dict,
        location: Location,
        retrieved_at: datetime | None = None,
    ) -> HourlyForecast:
        return HourlyForecast(
            location=location,
            weather_condition=self.parse_weather_condition(hour["weather"][0]),
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
        self,
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
        self,
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
        self,
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

    def flatten_to_mapped_data_buffer(self, data: dict[str, object]) -> dict[str, object]:
        current_weather = data["current_weather"]
        daily_forecast = data["daily_forecasts"][0]
        hourly_forecast = data["hourly_forecasts"][0]
        minutely_forecast = data["minutely_forecasts"][0]
        air_pollution = data["air_pollution"]
        weather_alerts = data["weather_alerts"]
        weather_alert = weather_alerts[0] if weather_alerts else None
        location = current_weather.location

        return {
            "location_city_name": location.city_name or "Warsaw",
            "location_country_code": location.country_code or "PL",
            "location_lat": location.lat,
            "location_lon": location.lon,
            "location_timezone": location.timezone,
            "location_timezone_offset": location.timezone_offset,
            "current_observed_at": current_weather.observed_at,
            "current_sunrise_at": current_weather.sunrise_at,
            "current_sunset_at": current_weather.sunset_at,
            "current_temp": current_weather.temp,
            "current_feels_like": current_weather.feels_like,
            "current_pressure": current_weather.pressure,
            "current_humidity": current_weather.humidity,
            "current_dew_point": current_weather.dew_point,
            "current_uvi": current_weather.uvi,
            "current_clouds": current_weather.clouds,
            "current_visibility": current_weather.visibility,
            "current_wind_speed": current_weather.wind_speed,
            "current_wind_deg": current_weather.wind_deg,
            "current_wind_gust": current_weather.wind_gust,
            "current_rain_1h": current_weather.rain_1h,
            "current_snow_1h": current_weather.snow_1h,
            "current_openweather_weather_id": (
                current_weather.weather_condition.openweather_weather_id
            ),
            "current_condition_main": current_weather.weather_condition.main,
            "current_condition_description": current_weather.weather_condition.description,
            "current_condition_icon": current_weather.weather_condition.icon,
            "daily_forecast_date": daily_forecast.forecast_date,
            "daily_retrieved_at": daily_forecast.retrieved_at,
            "daily_sunrise_at": daily_forecast.sunrise_at,
            "daily_sunset_at": daily_forecast.sunset_at,
            "daily_moonrise_at": daily_forecast.moonrise_at,
            "daily_moonset_at": daily_forecast.moonset_at,
            "daily_moonphase": daily_forecast.moonphase,
            "daily_temp_day": daily_forecast.temp_day,
            "daily_temp_min": daily_forecast.temp_min,
            "daily_temp_max": daily_forecast.temp_max,
            "daily_temp_night": daily_forecast.temp_night,
            "daily_temp_evening": daily_forecast.temp_evening,
            "daily_temp_morning": daily_forecast.temp_morning,
            "daily_feels_like_day": daily_forecast.feels_like_day,
            "daily_feels_like_night": daily_forecast.feels_like_night,
            "daily_pressure": daily_forecast.pressure,
            "daily_humidity": daily_forecast.humidity,
            "daily_dew_point": daily_forecast.dew_point,
            "daily_wind_speed": daily_forecast.wind_speed,
            "daily_wind_deg": daily_forecast.wind_deg,
            "daily_wind_gust": daily_forecast.wind_gust,
            "daily_clouds": daily_forecast.clouds,
            "daily_pop": daily_forecast.pop,
            "daily_rain": daily_forecast.rain,
            "daily_snow": daily_forecast.snow,
            "daily_uvi": daily_forecast.uvi,
            "daily_openweather_weather_id": daily_forecast.weather_condition.openweather_weather_id,
            "daily_condition_main": daily_forecast.weather_condition.main,
            "daily_condition_description": daily_forecast.weather_condition.description,
            "daily_condition_icon": daily_forecast.weather_condition.icon,
            "hourly_forecast_for": hourly_forecast.forecast_for,
            "hourly_retrieved_at": hourly_forecast.retrieved_at,
            "hourly_temp": hourly_forecast.temp,
            "hourly_feels_like": hourly_forecast.feels_like,
            "hourly_pressure": hourly_forecast.pressure,
            "hourly_humidity": hourly_forecast.humidity,
            "hourly_dew_point": hourly_forecast.dew_point,
            "hourly_uvi": hourly_forecast.uvi,
            "hourly_clouds": hourly_forecast.clouds,
            "hourly_visibility": hourly_forecast.visibility,
            "hourly_pop": hourly_forecast.pop,
            "hourly_wind_speed": hourly_forecast.wind_speed,
            "hourly_wind_deg": hourly_forecast.wind_deg,
            "hourly_wind_gust": hourly_forecast.wind_gust,
            "hourly_rain_1h": hourly_forecast.rain_1h,
            "hourly_snow_1h": hourly_forecast.snow_1h,
            "hourly_openweather_weather_id": (
                hourly_forecast.weather_condition.openweather_weather_id
            ),
            "hourly_condition_main": hourly_forecast.weather_condition.main,
            "hourly_condition_description": hourly_forecast.weather_condition.description,
            "hourly_condition_icon": hourly_forecast.weather_condition.icon,
            "minutely_forecast_for": minutely_forecast.forecast_for,
            "minutely_retrieved_at": minutely_forecast.retrieved_at,
            "minutely_precipitation": minutely_forecast.precipitation,
            "air_observed_at": air_pollution.observed_at,
            "air_aqi": air_pollution.aqi,
            "air_co": air_pollution.co,
            "air_no": air_pollution.no,
            "air_no2": air_pollution.no2,
            "air_o3": air_pollution.o3,
            "air_so2": air_pollution.so2,
            "air_pm2_5": air_pollution.pm2_5,
            "air_pm10": air_pollution.pm10,
            "air_nh3": air_pollution.nh3,
            "alert_sender_name": weather_alert.sender_name if weather_alert else None,
            "alert_event": weather_alert.event if weather_alert else None,
            "alert_start_at": weather_alert.start_at if weather_alert else None,
            "alert_end_at": weather_alert.end_at if weather_alert else None,
            "alert_description": weather_alert.description if weather_alert else None,
            "alert_tags": weather_alert.tags if weather_alert else None,
        }

    def parse_data(
        self,
        current_weather_data: dict,
        daily_forecast_data: dict,
        hourly_forecast_data: dict,
        minutely_forecast_data: dict,
        weather_alerts_data: dict,
        air_pollution_data: dict,
        city_name: str | None = None,
        country_code: str | None = None,
    ) -> dict[str, object]:
        location = self.parse_location(
            daily_forecast_data,
            city_name=city_name,
            country_code=country_code,
        )
        retrieved_at = datetime.now(UTC)

        return {
            "current_weather": self.parse_current_weather(
                current_weather_data,
                city_name=city_name,
                country_code=country_code,
            ),
            "daily_forecasts": [
                self.parse_daily_forecast(day, location, retrieved_at)
                for day in daily_forecast_data["daily"][:1]
            ],
            "hourly_forecasts": [
                self.parse_hourly_forecast(hour, location, retrieved_at)
                for hour in hourly_forecast_data["hourly"][:1]
            ],
            "minutely_forecasts": [
                self.parse_minutely_forecast(minute, location, retrieved_at)
                for minute in minutely_forecast_data["minutely"][:1]
            ],
            "weather_alerts": [
                self.parse_weather_alert(alert, location)
                for alert in weather_alerts_data.get("alerts", [])
            ],
            "air_pollution": self.parse_air_pollution(
                air_pollution_data,
                location,
            ),
        }
