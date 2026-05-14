"""Exceptions raised by pipeline components."""


class PostgresTableSourceError(RuntimeError):
    """Raised when a PostgreSQL table source cannot extract rows."""


class PostgresWarehouseSinkError(RuntimeError):
    """Raised when a PostgreSQL warehouse sink operation fails."""


class OpenWeatherApiSourceError(RuntimeError):
    """Raised when an OpenWeather API source cannot extract rows."""
