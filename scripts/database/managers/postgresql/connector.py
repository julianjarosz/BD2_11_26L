"""PostgreSQL connection lifecycle helpers."""

from __future__ import annotations

import typing

import psycopg
from psycopg.rows import dict_row

from scripts.errors.database_errors import DatabaseConnectionException


class PostgreSQLDatabaseConnector:
    """Owns opening and closing a PostgreSQL connection."""

    def __init__(
        self,
        dsn: str,
        *,
        autocommit: bool = False,
        **connection_kwargs: typing.Any,
    ) -> None:
        self.dsn: str = dsn
        self.autocommit: bool = autocommit
        self.connection_kwargs: dict[str, typing.Any] = connection_kwargs
        self.connection: psycopg.Connection | None = None

    def open_connection(self) -> psycopg.Connection:
        if self.connection is not None:
            raise RuntimeError("Busy resource: another PostgreSQL connection is already open.")

        try:
            self.connection = psycopg.connect(
                self.dsn,
                autocommit=self.autocommit,
                row_factory=dict_row,
                **self.connection_kwargs,
            )
        except psycopg.OperationalError as exc:
            raise DatabaseConnectionException("Could not connect to PostgreSQL database.") from exc

        return self.connection

    def get_connection(self) -> psycopg.Connection:
        if self.connection is None:
            raise DatabaseConnectionException("No PostgreSQL connection has been established.")
        return self.connection

    def close_connection(self) -> None:
        if self.connection is None:
            return

        try:
            self.connection.close()
        except psycopg.OperationalError as exc:
            raise DatabaseConnectionException(
                "Could not close PostgreSQL database connection."
            ) from exc
        finally:
            self.connection = None
