"""PostgreSQL implementation of the database manager interface.zw"""

from __future__ import annotations

import collections.abc
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

POSTGRES_DSN_ENV_VAR = "POSTGRES_DSN"


class PostgreSQLDatabaseManager(DatabaseManager):
    """Database manager backed by a PostgreSQL connection."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
        autocommit: bool = False,
        **connection_kwargs: typing.Any,
    ) -> None:
        """Create a PostgreSQL manager.

        Args:
            dsn: PostgreSQL connection string. If omitted, connection keyword
                arguments such as ``host``, ``port``, ``dbname``, ``user`` and
                ``password`` can be supplied.
            autocommit: Whether the connection should commit automatically.
            connection_kwargs: Additional arguments forwarded to psycopg.
        """
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
        columns = tuple(rows[0].keys())
        required_columns = set(columns)

        for row in rows:
            if set(row.keys()) != required_columns:
                raise ValueError("All rows must contain the same columns.")

        query = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values})").format(
            table=self._table_identifier(table_name),
            columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            values=sql.SQL(", ").join(sql.Placeholder(column) for column in columns),
        )

        try:
            with self.connection.cursor() as cursor:
                cursor.executemany(query, rows)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

        return len(rows)

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


    def _filter_columns(self, rows: list[DatabaseRow]) -> list[DatabaseRow]:
        final_columns: list[DatabaseRow] = []
        
        for row in rows:
            columns: set[str] = set(row.keys())
            
            
        return final_columns
            
            
            

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

        # Checking status of the columns 
        # What is status in this meaning ?
        # For example if not nullable columns are present in each row
        # Or if even row has any columns
        if not PostgreSQLDatabaseManager._check_for_columns(rows):
            raise ValueError("Rows must contain at least one column.")

        return rows

    @staticmethod
    def _table_identifier(table_name: str) -> sql.Identifier:
        table_parts = [part.strip() for part in table_name.split(".") if part.strip()]
        if not table_parts:
            raise ValueError("Table name cannot be empty.")
        return sql.Identifier(*table_parts)
