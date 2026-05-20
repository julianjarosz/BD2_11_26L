"""Async helpers for fetching current weather data from OpenWeather."""

import asyncio
import os
import random 
from collections import Counter
from typing import Any, final, Callable, Awaitable, Iterable
from dataclasses import dataclass
from scripts.api.api_data_struct import OpenWeatherData
from scripts.utils import fetch_config_value

import requests

OPENWEATHER_BASE_URL: str = fetch_config_value("consts.conf", "openweather.base_url")
API_KEY_ENV_VAR: str = fetch_config_value("consts.conf", "openweather.api_key_env_var")
DEFAULT_TIMEOUT_SECONDS: float = float(
    fetch_config_value("consts.conf", "openweather.default_timeout_seconds")
)
DEFAULT_CITY: str = fetch_config_value("consts.conf", "openweather.default_city")
        

@dataclass(slots=True)
class API_URL_KEY:
    base_url: str
    api_key: str
        
@final
class OpenWeatherFetchManager:

    def __init__(
        self,
        api_url_key_collection: list[API_URL_KEY],
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        assert (timeout) > 0.0
        self.timeout: float = timeout
        self.sessions: dict[API_URL_KEY, requests.Session] = {
            api_data: requests.Session() for api_data in api_url_key_collection
        }

    def _fetch_city_data_from_all_apis(self, city: str, **kwargs: dict[str, Any]) -> dict[str, dict]:
        api_response_from_url = {}
        for api_data, session in self.sessions.items():
            api_res: requests.Response = session.get(
                api_data.base_url,
                params={"q": city, "appid": api_data.api_key, **kwargs},
                timeout=self.timeout
            )
            api_res.raise_for_status()
            api_response_from_url[api_data.base_url] = api_res.json()
        
        return api_response_from_url
    
    def _take_value(self, values: list[Any]):
        if not values:
            return None 
        
        if all(val == values[0] for val in values):
            return values[0]
        
        if all(isinstance(val, int) for val in values):
            return max(values, key=values.count)
        
        if all(isinstance(val, float) for val in values):
            return sum(values) / len(values)
    
        random_idx: int = random.randint(a=0, b=len(values)-1)
        return values[random_idx]
    
    def _merge_data_from_api(self, city_data_from_apis: dict[str, dict]) -> OpenWeatherData:
        raw_data_buffer_fields: list[str] = ... # This function needs to know what fields it will be looking
        raw_buffer: dict[str, Any] = {}

        for raw_field in raw_data_buffer_fields:
            all_values: list[Any] = []
            
            for single_url_data in list(city_data_from_apis.values()):
                value: Any | None = single_url_data.get(raw_field, None)
                if value:
                    all_values.append(value)
                
            raw_buffer[raw_field] = self._take_value(all_values)

        return OpenWeatherData.from_api_response(raw_buffer)            
    
    def _fetch_data(self, city: str, **kwargs: dict[str, Any]) -> OpenWeatherData:
        data: dict = self._fetch_city_data_from_all_apis(city, **kwargs)
        openweather_data: OpenWeatherData = self._merge_data_from_api(data)
        return openweather_data

    async def fetch_city(self, city: str, **kwargs: dict[str, Any]) -> OpenWeatherData:
        """Fetch weather data for one city without blocking the event loop."""
        return await asyncio.to_thread(self._fetch_data, city, **kwargs)

    async def fetch_cities(
        self, cities: Iterable[str], **kwargs: Any
    ) -> list[OpenWeatherData]:
        """Fetch data from many cities without blocking the event loop."""
        tasks: list[Awaitable[OpenWeatherData]] = [
            self.fetch_city(city, **kwargs) for city in cities
        ]
        results = asyncio.gather(*tasks)
        return await results

    def close(self) -> None:
        """Close the underlying HTTP session."""
        for session in self.sessions:
            session.close()
