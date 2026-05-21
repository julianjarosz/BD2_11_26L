import configparser
import json

from pathlib import Path
from pprint import pprint
from urllib.request import urlopen

from api_struct import OpenWeatherDataParser


config = configparser.ConfigParser()

config.read(
    Path(__file__).parent / "api.conf"
)

api = config["openweather"]

api_key = api["OPENWEATHER_API_KEY"]


def fetch_json(url: str) -> dict:

    with urlopen(url) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def build_url(base_url: str) -> str:

    return base_url.format(
        OPENWEATHER_API_KEY=api_key
    )


def main():
    parser = OpenWeatherDataParser()

    data = parser.parse_data(
        current_weather_data=fetch_json(build_url(api["BASE_CURRENT_WEATHER"])),
        daily_forecast_data=fetch_json(build_url(api["BASE_DAILY_FORECAST"])),
        hourly_forecast_data=fetch_json(build_url(api["BASE_HOURLY_FORECAST"])),
        minutely_forecast_data=fetch_json(build_url(api["BASE_MINUTELY_FORECAST"])),
        weather_alerts_data=fetch_json(build_url(api["BASE_WEATHER_ALERTS"])),
        air_pollution_data=fetch_json(build_url(api["BASE_AIR_POLLUTION"])),
        city_name="Warsaw",
        country_code="PL",
    )

    pprint(data)


if __name__ == "__main__":
    main()
