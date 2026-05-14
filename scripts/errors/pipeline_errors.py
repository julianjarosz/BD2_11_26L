"""Exceptions raised by pipeline components."""


class PostgresTableSourceError(RuntimeError):
    """Raised when a PostgreSQL table source cannot extract rows."""


class PostgresWarehouseSinkError(RuntimeError):
    """Raised when a PostgreSQL warehouse sink operation fails."""
