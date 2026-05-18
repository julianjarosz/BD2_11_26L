from __future__ import annotations

from typing import Any, Collection, final

from psycopg import sql

from scripts.database.builders.base_query_builder import BaseQueryBuilder
from scripts.errors.database_errors import EmptyPayloadException
from scripts.database.models.database_types import DatabaseRow


@final
class BatchRowInsertQueryBuilder(
    BaseQueryBuilder[dict[tuple[str, ...], sql.Composed], dict[tuple[str, ...], tuple[Any, ...]]]
):
    """
    Build parameterized PostgreSQL INSERT queries for row batches grouped by columns.
    """

    __slots__ = ("_grouped_rows_by_columns",)

    def __init__(self, table_name: str, rows: Collection[DatabaseRow]) -> None:
        """
        Initialize the query builder.

        Parameters:
            table_name: Table name, optionally schema-qualified.
            rows: Rows to insert. Rows with different column sets are inserted by
                separate queries.

        Raises:
            InvalidTableException: If the table name is empty.
            EmptyPayloadException: If no rows are provided.
            ValueError: If any column name is empty.
        """
        self._grouped_rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]] = (
            self._group_rows_by_columns(rows)
        )
        super().__init__(table_name=table_name)

    @classmethod
    def _group_rows_by_columns(
        cls,
        rows: Collection[DatabaseRow],
    ) -> dict[tuple[str, ...], list[DatabaseRow]]:
        """
        Group non-empty rows by their sorted column-name tuple for batch inserts.
        """
        if len(rows) == 0:
            raise EmptyPayloadException("Cannot build insert queries for an empty payload.")

        grouped_rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]] = {}

        for row in rows:
            if not row:
                continue

            columns: tuple[str, ...] = tuple(sorted(row))
            cls._validate_columns(columns)

            grouped_rows_by_columns.setdefault(columns, []).append(row)

        return grouped_rows_by_columns

    def _build_query(self) -> dict[tuple[str, ...], sql.Composed]:
        """
        Build INSERT statements keyed by their column groups.
        """
        queries: dict[tuple[str, ...], sql.Composed] = {}

        for columns, grouped_rows in self._grouped_rows_by_columns.items():
            row_placeholders: sql.Composed = sql.SQL("({})").format(
                sql.SQL(", ").join(sql.Placeholder() for _ in columns)
            )
            queries[columns] = sql.SQL("INSERT INTO {} ({}) VALUES {}").format(
                self._table_identifier,
                sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                sql.SQL(", ").join(row_placeholders for _ in grouped_rows),
            )

        return queries

    def _build_params(self) -> dict[tuple[str, ...], tuple[Any, ...]]:
        """
        Build values ordered to match each grouped query's placeholders.
        """
        return {
            columns: tuple(row.get(column) for row in grouped_rows for column in columns)
            for columns, grouped_rows in self._grouped_rows_by_columns.items()
        }

    def get_grouped_rows_by_columns(self) -> dict[tuple[str, ...], list[DatabaseRow]]:
        """
        Return rows grouped by the column tuples used as query keys.
        """
        return self._grouped_rows_by_columns
