"""Database manager interface used by concrete database backends."""

from __future__ import annotations

import abc
import typing

DatabaseParams = typing.Sequence[typing.Any] | typing.Mapping[str, typing.Any]
DatabaseRow = typing.Mapping[str, typing.Any]
DatabaseRows = DatabaseRow | typing.Sequence[DatabaseRow]


class DatabaseManager(abc.ABC):
    """Interface for pushing data to and fetching data from a database."""

    @abc.abstractmethod
    def push_data(self, table_name: str, data: DatabaseRows) -> int:
        """Push one or more rows into ``table_name``.

        Returns the number of rows submitted to the database.
        """
        pass

    @abc.abstractmethod
    def fetch_data(
        self, query: str, params: DatabaseParams | None = None
    ) -> list[DatabaseRow]:
        """Fetch rows from the database using ``query`` and optional params."""
        pass

    @abc.abstractmethod
    def close(self) -> None:
        """Close database resources held by the manager."""

    @abc.abstractmethod
    def execute(
        self, query: str, params: DatabaseParams | None = None
    ) -> None:
        """Executes SQL command that does not return anything"""
        pass
