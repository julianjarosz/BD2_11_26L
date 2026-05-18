"""PostgreSQL implementation of the database manager interface."""

from __future__ import annotations

import dataclasses
import logging
import os
import typing

from typing import Any, cast

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from scripts.database.builders.batch_row_insert_query_builder import BatchRowInsertQueryBuilder
from scripts.database.builders.single_row_insert_query_builder import SingleRowInsertQueryBuilder
from scripts.database.builders.base_query_builder import BaseQueryBuilder
from scripts.database.managers.base_database_manager import (
    DatabaseManagerWithSchemaValidation,
    PreparedDatabasePayload,
)
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import (
    FailedRow,
    DatabaseParams,
    DatabaseRow,
)
from scripts.database.cleaners.data_schema_cleaner import CleaningResults, DataSchemaCleaner
from scripts.database.stores.schema_metadata_store import (
    SchemaMetadataStore,
    TableSchemaMetadata,
)
from scripts.errors.database_errors import (
    InvalidRequestType,
)
from scripts.utils import fetch_config_value
from scripts.database.models.database_types import DatabaseOperationResult
from scripts.database.models.query import Query
from scripts.database.checkers.query_checker import DatabaseQueryChecker

POSTGRES_DSN_ENV_VAR: str = fetch_config_value("consts.conf", "postgresql.dsn_env_var")
LOGGER: logging.Logger = logging.getLogger(__name__)


@dataclasses.dataclass
class PostgreSQLDatabaseManagerContext:
    is_low_frequency_data: bool
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

    __QUERY_BUILDERS: dict[str, type[BaseQueryBuilder[Any, Any]]] = {
        "SINGLE_ROW_QUERY": SingleRowInsertQueryBuilder,
        "BATCH_ROW_QUERY": BatchRowInsertQueryBuilder,
    }

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

    def _build_insert_query(
        self, table_name: str, query_builder_key: str, **builder_kwargs: dict[str, Any]
    ) -> BaseQueryBuilder[Any, Any]:
        """
        Build an insert query using the configured query-builder dispatch.
        """
        query_builder = self.__QUERY_BUILDERS.get(query_builder_key, None)
        if query_builder is None:
            raise ValueError(f"Unknown insert query builder: {query_builder_key}.")

        try:
            return query_builder(table_name=table_name, **builder_kwargs)
        except Exception:
            if self.logger is not None:
                self.logger.exception(
                    "Failed to build insert query: builder=%s table=%s kwargs=%s",
                    query_builder_key,
                    table_name,
                    builder_kwargs,
                )
            raise

    def _insert_single_rows(
        self, table_name: str, payload: DatabasePayload
    ) -> DatabaseOperationResult:
        """
        Insert payload rows one by one, committing successful rows individually.

        Parameters:
            table_name (str): Name of the table to insert data into.
            payload (DatabasePayload): Payload containing rows to insert.

        Returns:
            DatabaseOperationResult: Successful rows and rows that failed with their errors.
        """
        successful_rows: list[DatabaseRow] = []
        failed_rows: list[FailedRow] = []

        with self.connection.cursor() as cursor:
            for row in payload.rows:
                try:
                    builder = self._build_insert_query(
                        table_name,
                        "SINGLE_ROW_QUERY",
                        row=row,
                    )
                    cursor.execute(builder.get_query(), builder.get_params())
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
        builder: BatchRowInsertQueryBuilder = cast(
            BatchRowInsertQueryBuilder,
            self._build_insert_query(
                table_name,
                "BATCH_ROW_QUERY",
                rows=list(payload.rows),
            ),
        )
        grouped_rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]] = (
            builder.get_grouped_rows_by_columns()
        )
        queries_by_columns: dict[tuple[str, ...], sql.Composed] = builder.get_query()
        params_by_columns: dict[tuple[str, ...], tuple[Any, ...]] = builder.get_params()
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

                values: tuple[Any, ...] = params_by_columns[columns]

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
        """
        Validate table (if table exists)
        """
        # TODO - implement this method
        ...

    def _validate_payload(self, payload: DatabasePayload) -> None:
        """
        Validate payload (if it is not empty)
        """
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
                "To perform push operation payload needs insert_data request type",
                request_type=payload.request_type,
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
