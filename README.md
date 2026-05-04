# Data pipeline project for fetching and processing weather data
---
### In progress ...

## Configuration

Copy `scripts/api.conf.example` to `scripts/api.conf` for local development.

For secrets, prefer the `OPENWEATHER_API_KEY` environment variable over storing the key in the repository. The loader checks `OPENWEATHER_API_KEY` first and only falls back to `scripts/api.conf`.

For GitHub Actions, add `OPENWEATHER_API_KEY` as a repository secret if you later add workflow steps that call the OpenWeather API.
