from __future__ import annotations

from typing import Any, Mapping, final

from psycopg import sql

from scripts.database.builders.base_query_builder import BaseQueryBuilder
from scripts.errors.database_errors import EmptyRowException


@final
class SingleRowInsertQueryBuilder(BaseQueryBuilder[sql.Composed, tuple[Any, ...]]):
    """
    Build a parameterized PostgreSQL INSERT query for a single row.
    """

    __slots__ = ("_columns", "_row")

    def __init__(self, table_name: str, row: Mapping[str, Any]) -> None:
        """
        Initialize the query builder.

        Parameters:
            table_name: Table name, optionally schema-qualified.
            row: Mapping of column names to inserted values.

        Raises:
            InvalidTableException: If the table name is empty.
            ValueError: If any column name is empty.
            EmptyRowException: If the row has no columns.
        """
        if not row:
            raise EmptyRowException("Cannot build insert query for an empty row.", row=row)

        columns: tuple[str, ...] = tuple(row.keys())
        self._validate_columns(columns)

        self._columns: tuple[str, ...] = columns
        self._row: Mapping[str, Any] = row
        super().__init__(table_name=table_name)

    def _build_query(self) -> sql.Composed:
        """
        Build the INSERT statement for the configured table and columns.
        """
        return sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            self._table_identifier,
            sql.SQL(", ").join(sql.Identifier(column) for column in self._columns),
            sql.SQL(", ").join(sql.Placeholder() for _ in self._columns),
        )

    def _build_params(self) -> tuple[Any, ...]:
        """
        Build values ordered to match the query placeholders.
        """
        return tuple(self._row[column] for column in self._columns)
