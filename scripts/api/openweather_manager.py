import configparser
import json
import os

from pathlib import Path
from urllib.request import urlopen

from api_struct import OpenWeatherDataParser

OPENWEATHER_API_KEY_ENV_VAR = "OPENWEATHER_API_KEY"
DEFAULT_CITY_NAME = "Warsaw"
DEFAULT_COUNTRY_CODE = "PL"


class OpenWeatherManager:
    def __init__(
        self,
        config_path: Path | None = None,
        city_name: str = DEFAULT_CITY_NAME,
        country_code: str = DEFAULT_COUNTRY_CODE,
        parser: OpenWeatherDataParser | None = None,
    ) -> None:
        self.config = self.load_openweather_config(config_path)
        self.api_key = self.load_openweather_api_key(self.config)
        self.city_name = city_name
        self.country_code = country_code
        self.parser = parser or OpenWeatherDataParser()

    def get_data(self) -> dict[str, object]:
        parsed_data = self.parser.parse_data(
            current_weather_data=self.fetch_json(
                self.build_url(self.config["BASE_CURRENT_WEATHER"])
            ),
            daily_forecast_data=self.fetch_json(self.build_url(self.config["BASE_DAILY_FORECAST"])),
            hourly_forecast_data=self.fetch_json(
                self.build_url(self.config["BASE_HOURLY_FORECAST"])
            ),
            minutely_forecast_data=self.fetch_json(
                self.build_url(self.config["BASE_MINUTELY_FORECAST"])
            ),
            weather_alerts_data=self.fetch_json(self.build_url(self.config["BASE_WEATHER_ALERTS"])),
            air_pollution_data=self.fetch_json(self.build_url(self.config["BASE_AIR_POLLUTION"])),
            city_name=self.city_name,
            country_code=self.country_code,
        )

        current_weather = parsed_data["current_weather"]
        daily_forecast = parsed_data["daily_forecasts"][0]
        hourly_forecast = parsed_data["hourly_forecasts"][0]
        minutely_forecast = parsed_data["minutely_forecasts"][0]
        air_pollution = parsed_data["air_pollution"]
        weather_alerts = parsed_data["weather_alerts"]
        weather_alert = weather_alerts[0] if weather_alerts else None
        location = current_weather.location

        return {
            "location_city_name": location.city_name or DEFAULT_CITY_NAME,
            "location_country_code": location.country_code or DEFAULT_COUNTRY_CODE,
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

    @staticmethod
    def load_openweather_config(config_path: Path | None = None) -> configparser.SectionProxy:
        parser = configparser.ConfigParser()
        path = config_path or Path(__file__).with_name("api.conf")
        fallback_path = Path(__file__).with_name("api_example.conf")

        if not parser.read(path) and not parser.read(fallback_path):
            raise FileNotFoundError(f"OpenWeather config file not found: {path} or {fallback_path}")

        return parser["openweather"]

    @staticmethod
    def load_openweather_api_key(api_config: configparser.SectionProxy) -> str:
        api_key = os.getenv(OPENWEATHER_API_KEY_ENV_VAR, "").strip()
        if api_key:
            return api_key

        api_key = api_config.get("OPENWEATHER_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                f"OpenWeather API key not found in {OPENWEATHER_API_KEY_ENV_VAR} "
                "or scripts/api/api.conf."
            )

        return api_key

    @staticmethod
    def fetch_json(url: str) -> dict:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def build_url(self, base_url: str) -> str:
        return base_url.format(OPENWEATHER_API_KEY=self.api_key)
