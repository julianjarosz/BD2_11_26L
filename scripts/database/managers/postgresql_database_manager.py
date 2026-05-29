"""PostgreSQL implementation of the database manager interface."""

from __future__ import annotations

import dataclasses
import logging
import os
import typing

import psycopg
from psycopg.rows import dict_row

from scripts.database.builders.batch_row_insert_query_builder import BatchRowInsertQueryBuilder
from scripts.database.builders.single_row_insert_query_builder import SingleRowInsertQueryBuilder
from scripts.database.managers.base_database_manager import (
    DatabaseManagerWithSchemaValidation,
)
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import (
    DatabaseParams,
    DatabaseRequestType,
)
from scripts.database.cleaners.data_schema_cleaner import CleaningResults, DataSchemaCleaner
from scripts.database.stores.schema_metadata_store import (
    SchemaMetadataStore,
)
from scripts.errors.database_errors import (
    InvalidRequestType,
)
from scripts.utils import fetch_config_value
from scripts.database.models.database_types import DatabaseOperationResult
from scripts.database.models.query import Query
from scripts.database.checkers.query_checker import DatabaseQueryChecker
from scripts.database.executors.postgresql_query_executor import PostgreSQLQueryExecutor
from scripts.database.fetchers.base_fetcher import BaseFetcher
from scripts.database.fetchers.postgresql_fetcher import PostgreSQLDatabaseFetcher
from scripts.database.pushers.postgresql_pusher import PostgreSQLDatabasePusher

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


class PostgreSQLDatabaseConnector:
    def __init__(
        self, dsn: str, *, autocommit: bool, **connection_kwargs: dict[str, typing.Any]
    ) -> None:
        self.dsn: str = dsn
        self.autocommit: bool = autocommit
        self.connection_kwargs: dict[str, typing.Any] = connection_kwargs

        self.connection: psycopg.Connection | None = None

    def open_connection(self) -> None:
        if self.connection is not None:
            raise RuntimeError("Busy resource: Another connection already opened!")

        try:
            self.connection: psycopg.Connection = psycopg.connect(
                self.dsn, autocommit=self.autocommit, row_factory=dict_row
            )
        except Exception as e:
            ...

    def get_connection(self) -> psycopg.Connection:
        if self.connection is None:
            raise ValueError("No connection established!")
        return self.connection

    def close_connection(self) -> None:
        if self.connection is None:
            raise RuntimeError("No resource: No connection established!")

        try:
            self.connection.close()
            self.connection = None
        except Exception as e:
            ...


class PostgreSQLDatabaseManager(DatabaseManagerWithSchemaValidation):
    """Database manager backed by a PostgreSQL connection."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
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
        self.connector: PostgreSQLDatabaseConnector = PostgreSQLDatabaseConnector(
            dsn=dsn, autocommit=autocommit, connection_kwargs=connection_kwargs
        )
        self.connector.open_connection()

        self.query_executor: PostgreSQLQueryExecutor = PostgreSQLQueryExecutor(
            db_connection=self.connector.get_connection(),
            autocommit=autocommit,
        )
        self.single_row_inserter: PostgreSQLDatabasePusher = PostgreSQLDatabasePusher(
            query_executor=self.query_executor,
            builder_t=SingleRowInsertQueryBuilder,
        )
        self.batch_row_inserter: PostgreSQLDatabasePusher = PostgreSQLDatabasePusher(
            query_executor=self.query_executor,
            builder_t=BatchRowInsertQueryBuilder,
        )
        self.query_checker: DatabaseQueryChecker | None = query_checker

        self.fetcher: BaseFetcher[Query | str, DatabaseParams | None] = PostgreSQLDatabaseFetcher(
            query_executor=self.query_executor,
            logger=self.logger,
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

    def _insert_rows(self, table_name: str, payload: DatabasePayload) -> DatabaseOperationResult:
        rows = list(payload.rows)

        if len(rows) == 1:
            return self.single_row_inserter.insert(table_name=table_name, rows=rows)

        return self.batch_row_inserter.insert(table_name=table_name, rows=rows)

    def push_data(self, table_name: str, payload: DatabasePayload) -> DatabaseOperationResult:
        if payload.request_type != DatabaseRequestType.INSERT_DATA:
            raise InvalidRequestType(
                "To perform push operation payload needs insert_data request type",
                request_type=payload.request_type,
            )

        payload = self.payload_normalizer.normalize_payload(payload)
        self._log_payload_received(table_name, payload)

        cleaning_results: CleaningResults | None = None
        if self.data_schema_cleaner is not None:
            cleaning_results = self.data_schema_cleaner.clean_data(payload, table_name=table_name)

        prepared_payload = self._prepare_payload_for_operation(
            table_name=table_name,
            data=(cleaning_results.cleaned_payload if cleaning_results is not None else payload),
        )
        self._log_rejected_rows(table_name, prepared_payload.rejected_rows)
        validation_failed_rows = prepared_payload.failed_rows(table_name)

        if not prepared_payload.valid_rows:
            self._log_no_valid_rows(table_name, prepared_payload)
            return DatabaseOperationResult(
                successful_rows=[],
                failed_rows=(
                    validation_failed_rows
                    + (cleaning_results.failed_rows if cleaning_results is not None else [])
                ),
            )

        insertion_result: DatabaseOperationResult = self._insert_rows(
            table_name=table_name,
            payload=prepared_payload.valid_payload,
        )

        return DatabaseOperationResult(
            successful_rows=insertion_result.successful_rows,
            failed_rows=(
                insertion_result.failed_rows
                + validation_failed_rows
                + (cleaning_results.failed_rows if cleaning_results is not None else [])
            ),
        )

    def fetch_data(
        self, query: Query | str, params: DatabaseParams | None = None
    ) -> DatabaseOperationResult:
        if self.query_checker is not None:
            try:
                self.query_checker.safe_check_query(str(query))
            except Exception:
                if self.logger:
                    self.logger.exception("Query security check failed.")
                raise

        try:
            return self.fetcher.fetch(query, params)
        except Exception:
            if self.logger:
                self.logger.exception("Fetcher failed to execute query with params")
            raise

    def execute(self, query: str, params: DatabaseParams | None = None) -> None:
        """Run a SQL command that does not return rows."""
        self.query_executor.execute(query, params)

    def close(self) -> None:
        """Close the PostgreSQL connection."""
        self.connection.close()
