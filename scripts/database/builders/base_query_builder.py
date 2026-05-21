from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, final

from psycopg import sql

from scripts.errors.database_errors import InvalidTableException

QueryT = TypeVar("QueryT")
ParamsT = TypeVar("ParamsT")


class BaseQueryBuilder(ABC, Generic[QueryT, ParamsT]):
    """Interface for SQL query builders."""

    __slots__ = ("_params", "_table_identifier", "_table_name", "query")

    def __init__(self, table_name: str) -> None:
        if not table_name or not table_name.strip():
            raise InvalidTableException("Table name cannot be empty.", table=table_name)

        self._table_name: str = table_name
        self._table_identifier: sql.Identifier = self._build_table_identifier(table_name)
        self._params: ParamsT = self._build_params()
        self.query: QueryT = self._build_query()

    @final
    @staticmethod
    def _build_table_identifier(table_name: str) -> sql.Identifier:
        """
        Build a SQL identifier from an optional schema-qualified table name.
        """
        parts: tuple[str, ...] = tuple(
            part.strip() for part in table_name.split(".") if part.strip()
        )
        if not parts:
            raise InvalidTableException("Table name cannot be empty.", table=table_name)
        return sql.Identifier(*parts)

    @final
    @staticmethod
    def _validate_columns(columns: tuple[str, ...]) -> None:
        if any(not column or not column.strip() for column in columns):
            raise ValueError("Column names cannot be empty.")

    @abstractmethod
    def _build_query(self) -> QueryT:
        """Build and return a SQL query."""
        raise NotImplementedError

    @abstractmethod
    def _build_params(self) -> ParamsT:
        """Build and return params matching the query placeholders."""
        raise NotImplementedError

    @final
    def get_query(self) -> QueryT:
        """Return the built SQL query."""
        return self.query

    @final
    def get_params(self) -> ParamsT:
        """Return values ordered to match the query placeholders."""
        return self._params
