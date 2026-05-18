"""PostgreSQL implementation of the database manager interface."""

from __future__ import annotations

import dataclasses
import logging
import os
import typing

from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from scripts.database.base_database_manager import (
    DatabaseManagerWithSchemaValidation,
    PreparedDatabasePayload,
    RejectedDatabaseRow,
)
from scripts.database.database_payload import DatabasePayload
from scripts.database.database_types import (
    FailedRow,
    DatabaseRequestType,
    DatabaseParams,
    DatabaseRow,
    DatabaseRows,
)
from scripts.database.data_schema_cleaner import CleaningResults, DataSchemaCleaner
from scripts.database.schema_metadata_store import (
    ColumnMetadata,
    SchemaMetadataStore,
    TableSchemaMetadata,
)
from scripts.errors.database_errors import (
    CleaningException,
    EmptyPayloadException,
    EmptyRowException,
    InvalidRequestType,
)
from scripts.utils import fetch_config_value
from scripts.database.database_types import DatabaseOperationResult
from scripts.database.query import Query
from scripts.database.query_checker import DatabaseQueryChecker

POSTGRES_DSN_ENV_VAR: str = fetch_config_value("consts.conf", "postgresql.dsn_env_var")
LOGGER: logging.Logger = logging.getLogger(__name__)


@dataclasses.dataclass
class PostgreSQLDatabaseManagerContext:
    autocommit: bool
    schema_metadata_store: SchemaMetadataStore | None
    data_schema_cleaner: DataSchemaCleaner | None
    logger: logging.Logger
    connection_kwargs: dict[str, typing.Any]

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "autocommit": self.autocommit,
            "schema_metadata_store": self.schema_metadata_store,
            "data_schema_cleaner": self.data_schema_cleaner,
            "logger": self.logger,
            **self.connection_kwargs,
        }


class PostgreSQLDatabaseManager(DatabaseManagerWithSchemaValidation):
    """Database manager backed by a PostgreSQL connection."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
        is_low_frequency_data: bool = False,
        autocommit: bool = False,
        schema_metadata_store: SchemaMetadataStore | None = None,
        data_schema_cleaner: DataSchemaCleaner | None = None,
        query_checker: DatabaseQueryChecker | None = None,
        logger: logging.Logger | None = None,
        **connection_kwargs: dict[str, typing.Any],
    ) -> None:

        super().__init__(
            schema_metadata_store=schema_metadata_store,
            data_schema_cleaner=data_schema_cleaner,
            logger=logger,
            default_logger=LOGGER,
        )
        self.is_low_frequency_data: bool = is_low_frequency_data
        self.query_checker: DatabaseQueryChecker | None = query_checker
        self.connection: psycopg.Connection = psycopg.connect(
            dsn,
            autocommit=autocommit,
            row_factory=dict_row,
            **connection_kwargs,
        )

    @classmethod
    def create_from_env(
        cls, context: PostgreSQLDatabaseManagerContext, env_var: str = POSTGRES_DSN_ENV_VAR
    ) -> "PostgreSQLDatabaseManager":
        """
        Create a PostgreSQL Database Manager from environment variables.
        """
        dsn: str = os.getenv(env_var, "").strip()
        if not dsn:
            raise ValueError(f"PostgreSQL DSN not found in environment variable {env_var}.")
        return cls(dsn=dsn, **context.to_dict())

    @staticmethod
    def _table_identifier(table_name: str) -> sql.Identifier:
        """
        Build a SQL identifier from an optional schema-qualified table name.
        """
        table_parts: list[str] = [part.strip() for part in table_name.split(".") if part.strip()]
        if not table_parts:
            raise ValueError("Table name cannot be empty.")
        return sql.Identifier(*table_parts)

    def _build_single_row_insert_query(
        self, table_name: str, row: DatabaseRow
    ) -> tuple[sql.Composed, tuple[Any, ...]]:
        """
        Build a parameterized INSERT query for a single database row.
        Note: Use this function when sources provides single row of data ever and again.

        Parameters:
            table_name (str): Name of the table to insert data into.
            row (DatabaseRow): Mapping of column names to values for the inserted row.

        Raises:
            EmptyRowException: If row does not contain any values.
            Exceptions connnected to invalid creation of inserting query

        Returns:
            sql.Composed, tuple[Any, ...]: INSERT statement with quoted identifiers and placeholders.
        """
        if not row:
            raise EmptyRowException("Cannot build insert query for an empty row.", row=row)

        columns: tuple[str, ...] = tuple(row.keys())
        values: tuple[Any, ...] = tuple(row.values())
        try:
            query: sql.Composed = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                PostgreSQLDatabaseManager._table_identifier(table_name),
                sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                sql.SQL(", ").join(sql.Placeholder() for _ in values),
            )

            return query, values
        except Exception:
            if self.logger is not None:
                self.logger.exception(
                    "Failed to build insert query: table=%s columns=%s row=%s",
                    table_name,
                    columns,
                    row,
                )
            raise

    def _group_rows_by_columns(
        self, payload: DatabasePayload
    ) -> dict[tuple[str, ...], list[DatabaseRow]]:
        """
        Group payload rows by their sorted column-name tuple.

        Parameters:
            payload (DatabasePayload): Payload containing rows to group.

        Raises:
            EmptyPayloadException: If the payload contains no rows.

        Returns:
            dict[tuple[str, ...], list[DatabaseRow]]: Rows keyed by their column names.
        """
        if payload.number_of_rows == 0:
            raise EmptyPayloadException("Your payload is empty, no rows to group.", payload=payload)

        grouped_rows: dict[tuple[str, ...], list[DatabaseRow]] = {}

        for row_index, row in enumerate(payload.rows):
            if not row and self.logger is not None:
                self.logger.warning(
                    "Skipping payload row at index %s because it has no columns.",
                    row_index,
                )
                continue

            columns: tuple[str, ...] = tuple(sorted(row))
            grouped_rows.setdefault(columns, []).append(row)

        return grouped_rows

    @staticmethod
    def _build_insert_queries_for_column_groups(
        table_name: str, grouped_rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]]
    ) -> dict[tuple[str, ...], sql.Composed]:
        """
        Build parameterized INSERT queries for row groups sharing the same columns.
        Note: Use this function when data is coming in batches.

        Parameters:
            table_name (str): Name of the table to insert data into.
            grouped_rows_by_columns (dict[tuple[str, ...], list[DatabaseRow]]): Rows keyed by
                their column-name tuple.

        Returns:
            dict[tuple[str, ...], sql.Composed]: INSERT statements keyed by their column groups.
        """
        table_identifier: sql.Identifier = PostgreSQLDatabaseManager._table_identifier(table_name)
        queries: dict[tuple[str, ...], sql.Composed] = {}

        for columns, grouped_rows in grouped_rows_by_columns.items():
            if not columns or not grouped_rows:
                continue

            row_placeholders: sql.Composed = sql.SQL("({})").format(
                sql.SQL(", ").join(sql.Placeholder() for _ in columns)
            )
            queries[columns] = sql.SQL("INSERT INTO {} ({}) VALUES {}").format(
                table_identifier,
                sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                sql.SQL(", ").join(row_placeholders for _ in grouped_rows),
            )

        return queries

    def _insert_single_rows(
        self, table_name: str, payload: DatabasePayload
    ) -> DatabaseOperationResult:
        successful_rows: list[DatabaseRow] = []
        failed_rows: list[FailedRow] = []

        with self.connection.cursor() as cursor:
            for row in payload.rows:
                try:
                    query, values = self._build_single_row_insert_query(table_name, row)
                    cursor.execute(query, values)
                    if not self.connection.autocommit:
                        self.connection.commit()
                except Exception as exc:
                    if not self.connection.autocommit:
                        self.connection.rollback()
                    failed_rows.append(
                        FailedRow(
                            table_name=table_name,
                            row=row,
                            message="Failed to insert row.",
                            exception=exc,
                        )
                    )
                else:
                    successful_rows.append(row)

        return DatabaseOperationResult(successful_rows=successful_rows, failed_rows=failed_rows)

    def _insert_grouped_rows(
        self, table_name: str, payload: DatabasePayload
    ) -> DatabaseOperationResult:
        """
        Insert payload rows in batches grouped by matching column sets..

        Parameters:
            table_name (str): Name of the table to insert data into.
            payload (DatabasePayload): Payload containing rows to insert.

        Returns:
            DatabaseOperationResult: Successful rows and failed rows from the grouped inserts.
        """
        grouped_rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]] = (
            self._group_rows_by_columns(payload)
        )
        queries_by_columns: dict[tuple[str, ...], sql.Composed] = (
            self._build_insert_queries_for_column_groups(
                table_name,
                grouped_rows_by_columns,
            )
        )
        successful_rows: list[DatabaseRow] = []
        failed_rows: list[FailedRow] = []

        with self.connection.cursor() as cursor:

            for columns, query in queries_by_columns.items():
                grouped_rows: list[DatabaseRow] | None = grouped_rows_by_columns.get(columns, None)

                if grouped_rows is None:
                    if self.logger is not None:
                        self.logger.warning(
                            "Skipping insert query without matching grouped rows: table=%s columns=%s",
                            table_name,
                            columns,
                        )
                    continue

                values: tuple[Any, ...] = tuple(
                    row.get(column) for row in grouped_rows for column in columns
                )

                try:
                    cursor.execute(query, values)
                    if not self.connection.autocommit:
                        self.connection.commit()
                except Exception as exc:
                    if not self.connection.autocommit:
                        self.connection.rollback()
                    failed_rows.extend(
                        FailedRow(
                            table_name=table_name,
                            row=row,
                            message="Failed to insert row group.",
                            exception=exc,
                        )
                        for row in grouped_rows
                    )
                else:
                    successful_rows.extend(grouped_rows)

        return DatabaseOperationResult(successful_rows=successful_rows, failed_rows=failed_rows)

    def _insert_rows(self, table_name: str, payload: DatabasePayload) -> DatabaseOperationResult:
        if payload.number_of_rows == 0:
            return DatabaseOperationResult(successful_rows=[], failed_rows=[])

        if self.is_low_frequency_data:
            return self._insert_single_rows(table_name, payload)

        return self._insert_grouped_rows(table_name, payload)

    def _validate_table(self, table_name: str) -> None:
        """Validate table (if table exists)"""
        # TODO - implement this method
        ...

    def _validate_payload(self, payload: DatabasePayload) -> None:
        """Validate payload (if it is not empty)"""
        # TODO - implement thie method
        ...

    def push_data(self, table_name: str, payload: DatabasePayload) -> DatabaseOperationResult:
        """
        Method for inserting data into your PostgreSQL database.

        Parameters:
            * table_name (str): Name of the table data is going to be inserted
            * data (DatabasePayload): Payload containing data to insert into database

        Raises:
            * InvalidRequestType - if payload does not have correct request type
            * Other exceptions from validation methods

        Returns:
            DatabaseOperationResult: Result of insert operation performed on your database
        """
        if payload.request_type != "insert_data":
            raise InvalidRequestType(
                "To perform push operation payload needs insert_data request type"
            )

        try:
            # TODO - add validation methods
            self._validate_table(table_name)
            self._validate_payload(payload)
        except Exception:
            if self.logger is not None:
                self.logger.exception(
                    "Failed initial validation before inserting database payload: table=%s",
                    table_name,
                )
            raise

        cleaning_results: CleaningResults | None = None
        if self.data_schema_cleaner is not None:
            cleaning_results = self.data_schema_cleaner.clean_data(payload, table_name=table_name)

        insertion_result: DatabaseOperationResult = self._insert_rows(
            table_name,
            (cleaning_results.cleaned_payload if cleaning_results is not None else payload),
        )

        return DatabaseOperationResult(
            successful_rows=insertion_result.successful_rows,
            failed_rows=(
                insertion_result.failed_rows
                + (cleaning_results.failed_rows if cleaning_results is not None else [])
            ),
        )

    def fetch_data(
        self, query: Query | str, params: DatabaseParams | None = None
    ) -> DatabaseOperationResult:
        """
        Method for fetching data from your PostgreSQL database.

        Parameters:
            * query (Query | str) - Query to be executed while fetching data
            * params (DatabaseParams | None) - Additional params for fetching database rows

        Raises:
            * Exceptions connected to Query Security Check, if checker is present

        Returns:
            DatabaseOperationResult - Result of fetch operation performed on your database
        """
        if self.query_checker is not None:
            try:
                self.query_checker.safe_check_query(str(query))
            except Exception:
                self.logger.exception("Query security check failed.")
                raise

        with self.connection.cursor() as cursor:
            try:
                cursor.execute(str(query), params)
            except Exception:
                self.logger.exception("Cursor failed to execute query with params")
                raise

            successful_rows: list[DatabaseRow] = []
            failed_rows: list[FailedRow] = []

            # Eeeee - needs refactoring there
            while row := cursor.fetchone():
                try:
                    successful_rows.append(typing.cast(DatabaseRow, row))
                except Exception as exc:
                    failed_rows.append(
                        FailedRow(
                            table_name="",
                            row=typing.cast(DatabaseRow, row),
                            message="Fetched row failed validation",
                            exception=exc,
                        )
                    )

            return DatabaseOperationResult(
                successful_rows=successful_rows,
                failed_rows=failed_rows,
            )

    def cache_table_schema(self, table_name: str) -> TableSchemaMetadata:
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

    def execute(self, query: str, params: DatabaseParams | None = None) -> None:
        """Run a SQL command that does not return rows."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def close(self) -> None:
        """Close the PostgreSQL connection."""
        self.connection.close()