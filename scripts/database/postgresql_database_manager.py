"""PostgreSQL implementation of the database manager interface."""

from __future__ import annotations

import collections.abc
import dataclasses
import logging
import os
import typing

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from scripts.database.database_manager import (
    DatabaseManager,
    DatabaseParams,
    DatabaseRow,
    DatabaseRows,
)
from scripts.database.schema_metadata_store import (
    ColumnMetadata,
    SchemaMetadataStore,
    TableSchemaMetadata,
)

POSTGRES_DSN_ENV_VAR = "POSTGRES_DSN"
LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class RejectedDatabaseRow:
    """Row rejected before insertion and the reason why."""

    row: DatabaseRow
    reason: str


class PostgreSQLDatabaseManager(DatabaseManager):
    """Database manager backed by a PostgreSQL connection."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
        autocommit: bool = False,
        schema_metadata_store: SchemaMetadataStore | None = None,
        logger: logging.Logger | None = None,
        **connection_kwargs: typing.Any,
    ) -> None:
        """Create a PostgreSQL manager.

        Args:
            dsn: PostgreSQL connection string. If omitted, connection keyword
                arguments such as ``host``, ``port``, ``dbname``, ``user`` and
                ``password`` can be supplied.
            autocommit: Whether the connection should commit automatically.
            schema_metadata_store: Optional metadata store used to validate rows
                before inserting them.
            logger: Optional logger for rejected row messages.
            connection_kwargs: Additional arguments forwarded to psycopg.
        """
        self.schema_metadata_store = schema_metadata_store
        self.logger = logger or LOGGER
        self.connection = psycopg.connect(
            dsn,
            autocommit=autocommit,
            row_factory=dict_row,
            **connection_kwargs,
        )

    @classmethod
    def from_env(
        cls, env_var: str = POSTGRES_DSN_ENV_VAR
    ) -> "PostgreSQLDatabaseManager":
        """Create a manager from a PostgreSQL DSN stored in an environment variable."""
        dsn = os.getenv(env_var, "").strip()
        if not dsn:
            raise ValueError(
                f"PostgreSQL DSN not found in environment variable {env_var}."
            )
        return cls(dsn)

    def push_data(self, table_name: str, data: DatabaseRows) -> int:
        """Insert one or more mapping rows into a PostgreSQL table."""
        rows = self._normalize_rows(data)
        rows, rejected_rows = self._filter_invalid_rows(table_name, rows)
        self._log_rejected_rows(table_name, rejected_rows)
        if not rows:
            return 0

        rows_by_columns = self._group_rows_by_columns(rows)

        try:
            with self.connection.cursor() as cursor:
                for columns, grouped_rows in rows_by_columns.items():
                    query = sql.SQL(
                        "INSERT INTO {table} ({columns}) VALUES ({values})"
                    ).format(
                        table=self._table_identifier(table_name),
                        columns=sql.SQL(", ").join(
                            sql.Identifier(column) for column in columns
                        ),
                        values=sql.SQL(", ").join(
                            sql.Placeholder(column) for column in columns
                        ),
                    )
                    cursor.executemany(query, grouped_rows)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

        return len(rows)

    def cache_table_schema(self, table_name: str) -> TableSchemaMetadata:
        """Fetch table schema from PostgreSQL and cache it in the metadata store."""
        if self.schema_metadata_store is None:
            raise ValueError("Schema metadata store is not configured.")

        schema_name, short_table_name = self._split_table_name(table_name)
        rows = self.fetch_data(
            """
            SELECT column_name, data_type, is_nullable, column_default, is_identity
            FROM information_schema.columns
            WHERE table_schema = %(schema_name)s
              AND table_name = %(table_name)s
            ORDER BY ordinal_position
            """,
            {"schema_name": schema_name, "table_name": short_table_name},
        )
        if not rows:
            raise ValueError(f"Table schema not found for {table_name}.")

        schema = TableSchemaMetadata(
            table_name=table_name,
            columns=tuple(
                ColumnMetadata(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    is_nullable=row["is_nullable"] == "YES",
                    has_default=row["column_default"] is not None,
                    is_identity=row["is_identity"] == "YES",
                )
                for row in rows
            ),
        )
        self.schema_metadata_store.set_table_schema(schema)
        return schema

    def fetch_data(
        self,
        query: str,
        params: DatabaseParams | None = None,
    ) -> list[DatabaseRow]:
        """Run a read query and return rows as dictionaries."""
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return list(cursor.fetchall())

    def close(self) -> None:
        """Close the PostgreSQL connection."""
        self.connection.close()

    def __enter__(self) -> "PostgreSQLDatabaseManager":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: typing.Any,
    ) -> None:
        self.close()

    def execute(self, query: str, params: DatabaseParams | None = None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execture(query, params)
            self.connection.commit()
        except Exception:
            self.connection.rollback()

    def _filter_invalid_rows(
        self, table_name: str, rows: list[DatabaseRow]
    ) -> tuple[list[DatabaseRow], list[RejectedDatabaseRow]]:
        if self.schema_metadata_store is None:
            return rows, []

        schema = self.schema_metadata_store.get_table_schema(table_name)
        if schema is None:
            self.logger.warning(
                "Schema metadata for table %s was not found. Skipping row validation.",
                table_name,
            )
            return rows, []

        valid_rows: list[DatabaseRow] = []
        rejected_rows: list[RejectedDatabaseRow] = []
        known_columns = schema.column_names
        required_columns = schema.required_column_names

        for row in rows:
            row_columns = set(row.keys())
            unknown_columns = row_columns - known_columns
            missing_required_columns = required_columns - row_columns

            if unknown_columns:
                rejected_rows.append(
                    RejectedDatabaseRow(
                        row=row,
                        reason=f"unknown columns: {', '.join(sorted(unknown_columns))}",
                    )
                )
                continue

            if missing_required_columns:
                rejected_rows.append(
                    RejectedDatabaseRow(
                        row=row,
                        reason=(
                            "missing required columns: "
                            f"{', '.join(sorted(missing_required_columns))}"
                        ),
                    )
                )
                continue

            valid_rows.append(row)

        return valid_rows, rejected_rows

    def _log_rejected_rows(
        self, table_name: str, rejected_rows: list[RejectedDatabaseRow]
    ) -> None:
        for rejected_row in rejected_rows:
            self.logger.warning(
                "Rejected row for table %s before insert: %s. Row: %s",
                table_name,
                rejected_row.reason,
                rejected_row.row,
            )

    @staticmethod
    def _normalize_rows(data: DatabaseRows) -> list[DatabaseRow]:
        if isinstance(data, collections.abc.Mapping):
            rows = [data]
        else:
            rows = list(data)

        if not rows:
            raise ValueError("At least one row is required to push data.")

        if not all(isinstance(row, collections.abc.Mapping) for row in rows):
            raise TypeError("Rows must be mappings of column names to values.")

        if not rows[0]:
            raise ValueError("Rows must contain at least one column.")

        return rows

    @staticmethod
    def _group_rows_by_columns(
        rows: list[DatabaseRow],
    ) -> dict[tuple[str, ...], list[DatabaseRow]]:
        rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]] = {}
        for row in rows:
            columns = tuple(row.keys())
            rows_by_columns.setdefault(columns, []).append(row)
        return rows_by_columns

    @staticmethod
    def _table_identifier(table_name: str) -> sql.Identifier:
        table_parts = [part.strip() for part in table_name.split(".") if part.strip()]
        if not table_parts:
            raise ValueError("Table name cannot be empty.")
        return sql.Identifier(*table_parts)

    @staticmethod
    def _split_table_name(table_name: str) -> tuple[str, str]:
        table_parts = [part.strip() for part in table_name.split(".") if part.strip()]
        if len(table_parts) == 1:
            return "public", table_parts[0]
        if len(table_parts) == 2:
            return table_parts[0], table_parts[1]
        raise ValueError("Table name can contain at most schema and table parts.")
