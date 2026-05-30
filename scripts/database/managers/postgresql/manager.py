"""PostgreSQL implementation of the database manager interface."""

from __future__ import annotations

import os
import typing

from scripts.database.builders.batch_row_insert_query_builder import BatchRowInsertQueryBuilder
from scripts.database.builders.single_row_insert_query_builder import SingleRowInsertQueryBuilder
from scripts.database.checkers.query_checker import DatabaseQueryChecker
from scripts.database.cleaners.data_schema_cleaner import CleaningResults, DataSchemaCleaner
from scripts.database.executors.postgresql_query_executor import PostgreSQLQueryExecutor
from scripts.database.fetchers.base_fetcher import BaseFetcher
from scripts.database.fetchers.postgresql_fetcher import PostgreSQLDatabaseFetcher
from scripts.database.managers.base import (
    DatabaseManagerInterface,
    DatabaseManagerLoggerInterface,
    DatabasePayloadPreparer,
    log_database_lifecycle,
)
from scripts.database.managers.postgresql.connector import PostgreSQLDatabaseConnector
from scripts.database.managers.postgresql.context import PostgreSQLDatabaseManagerContext
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import (
    DatabaseOperationResult,
    DatabaseParams,
    DatabaseRequestType,
)
from scripts.database.models.query import Query
from scripts.database.pushers.postgresql_pusher import PostgreSQLDatabasePusher
from scripts.database.stores.schema_metadata_store import (
    SchemaMetadataStore,
)
from scripts.errors.database_errors import (
    DatabaseConnectionException,
    InvalidRequestType,
)
from scripts.utils import fetch_config_value
from scripts.database.models.database_types import FailedRow
from scripts.database.managers.base.tools.payload import PreparedDatabasePayload

POSTGRES_DSN_ENV_VAR: str = fetch_config_value("consts.conf", "postgresql.dsn_env_var")


class PostgreSQLDatabaseManager(DatabaseManagerInterface):
    """Database manager backed by a PostgreSQL connection."""

    manager_name: str = "postgresql"

    def __init__(
        self,
        dsn: str | None = None,
        *,
        autocommit: bool = False,
        schema_metadata_store: SchemaMetadataStore | None = None,
        data_schema_cleaner: DataSchemaCleaner | None = None,
        query_checker: DatabaseQueryChecker | None = None,
        database_logger: DatabaseManagerLoggerInterface | None = None,
        connector: PostgreSQLDatabaseConnector | None = None,
        payload_preparer: DatabasePayloadPreparer | None = None,
        **connection_kwargs: typing.Any,
    ) -> None:
        self.database_logger: DatabaseManagerLoggerInterface | None = database_logger
        self.data_schema_cleaner: DataSchemaCleaner | None = data_schema_cleaner
        self.payload_preparer: DatabasePayloadPreparer = (
            payload_preparer
            or DatabasePayloadPreparer(
                schema_metadata_store=schema_metadata_store,
            )
        )
        if connector is None:
            if dsn is None:
                raise ValueError("PostgreSQL DSN is required when connector is not provided.")
            connector = PostgreSQLDatabaseConnector(
                dsn=dsn,
                autocommit=autocommit,
                **connection_kwargs,
            )
        self.connector: PostgreSQLDatabaseConnector = connector

        self.query_executor: PostgreSQLQueryExecutor | None = None
        self.single_row_inserter: PostgreSQLDatabasePusher | None = None
        self.batch_row_inserter: PostgreSQLDatabasePusher | None = None
        self.query_checker: DatabaseQueryChecker | None = query_checker
        self.fetcher: BaseFetcher[Query | str, DatabaseParams | None] | None = None

    @log_database_lifecycle(
        started="connect_started",
        succeeded="connect_succeeded",
        failed="connect_failed",
    )
    def open(self) -> "PostgreSQLDatabaseManager":
        try:
            self.connector.open_connection()
            self.query_executor = PostgreSQLQueryExecutor(
                db_connection=self.connector.get_connection(),
                autocommit=self.connector.autocommit,
            )
            self.single_row_inserter = PostgreSQLDatabasePusher(
                query_executor=self.query_executor,
                builder_t=SingleRowInsertQueryBuilder,
            )
            self.batch_row_inserter = PostgreSQLDatabasePusher(
                query_executor=self.query_executor,
                builder_t=BatchRowInsertQueryBuilder,
            )
            self.fetcher = PostgreSQLDatabaseFetcher(
                query_executor=self.query_executor,
            )
        except Exception as exc:
            try:
                self.connector.close_connection()
            except Exception:
                pass
            finally:
                self._clear_runtime_dependencies()
            raise

        return self

    def __enter__(self) -> "PostgreSQLDatabaseManager":
        return self.open()

    def _ensure_connected(self) -> None:
        if (
            self.query_executor is None
            or self.single_row_inserter is None
            or self.batch_row_inserter is None
            or self.fetcher is None
        ):
            raise DatabaseConnectionException(
                "PostgreSQL manager is not connected. Use it as a context manager "
                "or call open() before executing database operations."
            )

    def _get_query_executor(self) -> PostgreSQLQueryExecutor:
        self._ensure_connected()
        return typing.cast(PostgreSQLQueryExecutor, self.query_executor)

    def _get_fetcher(self) -> BaseFetcher[Query | str, DatabaseParams | None]:
        self._ensure_connected()
        return typing.cast(BaseFetcher[Query | str, DatabaseParams | None], self.fetcher)

    def _get_insert_pushers(
        self,
    ) -> tuple[PostgreSQLDatabasePusher, PostgreSQLDatabasePusher]:
        self._ensure_connected()
        return (
            typing.cast(PostgreSQLDatabasePusher, self.single_row_inserter),
            typing.cast(PostgreSQLDatabasePusher, self.batch_row_inserter),
        )

    @classmethod
    def create_from_env(
        cls, context: PostgreSQLDatabaseManagerContext, env_var: str = POSTGRES_DSN_ENV_VAR
    ) -> "PostgreSQLDatabaseManager":
        """Create a PostgreSQL Database Manager from environment variables."""
        dsn: str = os.getenv(env_var, "").strip()
        if not dsn:
            raise ValueError(f"PostgreSQL DSN not found in environment variable {env_var}.")
        return cls(dsn=dsn, **context.to_dict())

    def _insert_rows(self, table_name: str, payload: DatabasePayload) -> DatabaseOperationResult:
        single_row_inserter, batch_row_inserter = self._get_insert_pushers()
        rows = list(payload.rows)

        if len(rows) == 1:
            return single_row_inserter.insert(table_name=table_name, rows=rows)

        return batch_row_inserter.insert(table_name=table_name, rows=rows)

    def _prepare_payload_for_push(
        self,
        table_name: str,
        payload: DatabasePayload,
    ) -> tuple[PreparedDatabasePayload, list[FailedRow]]:
        cleaning_results: CleaningResults | None = None

        if self.data_schema_cleaner is not None:
            cleaning_results = self.data_schema_cleaner.clean_data(payload, table_name=table_name)

        prepared_payload: PreparedDatabasePayload = self.payload_preparer.prepare(
            table_name=table_name,
            data=cleaning_results.cleaned_payload if cleaning_results is not None else payload,
        )

        failed_rows: list[FailedRow] = prepared_payload.failed_rows(table_name)
        if cleaning_results is not None:
            failed_rows += cleaning_results.failed_rows

        return prepared_payload, failed_rows

    def push_data(self, table_name: str, payload: DatabasePayload) -> DatabaseOperationResult:
        if payload.request_type != DatabaseRequestType.INSERT_DATA:
            raise InvalidRequestType(
                "To perform push operation payload needs insert_data request type",
                request_type=payload.request_type,
            )

        try:
            self._ensure_connected()
            payload: DatabasePayload = self.payload_preparer.payload_normalizer.normalize_payload(
                payload
            )

            if self.database_logger is not None:
                self.database_logger.push_started(
                    self.manager_name,
                    table_name,
                    payload.number_of_rows,
                )

            prepared_payload, failed_rows = self._prepare_payload_for_push(table_name, payload)

            if not prepared_payload.valid_rows:
                result: DatabaseOperationResult = DatabaseOperationResult(
                    successful_rows=[],
                    failed_rows=failed_rows,
                )

                if self.database_logger is not None:
                    self.database_logger.push_succeeded(self.manager_name, table_name, result)

                return result

            insertion_result: DatabaseOperationResult = self._insert_rows(
                table_name=table_name,
                payload=prepared_payload.valid_payload,
            )

            result = DatabaseOperationResult(
                successful_rows=insertion_result.successful_rows,
                failed_rows=(insertion_result.failed_rows + failed_rows),
            )

        except Exception as exc:
            if self.database_logger is not None:
                self.database_logger.push_failed(self.manager_name, table_name, exc)
            raise

        if self.database_logger is not None:
            self.database_logger.push_succeeded(self.manager_name, table_name, result)

        return result

    def fetch_data(
        self, query: Query | str, params: DatabaseParams | None = None
    ) -> DatabaseOperationResult:
        try:
            fetcher = self._get_fetcher()
            if self.database_logger is not None:
                self.database_logger.fetch_started(self.manager_name, query)

            if self.query_checker is not None:
                self.query_checker.safe_check_query(str(query))

            result = fetcher.fetch(query, params)
        except Exception as exc:
            if self.database_logger is not None:
                self.database_logger.fetch_failed(self.manager_name, query, exc)
            raise

        if self.database_logger is not None:
            self.database_logger.fetch_succeeded(self.manager_name, result)
        return result

    def execute(self, query: str, params: DatabaseParams | None = None) -> None:
        """Run a SQL command that does not return rows."""
        try:
            if self.database_logger is not None:
                self.database_logger.execute_started(self.manager_name, query)
            self._get_query_executor().execute(query, params)
        except Exception as exc:
            if self.database_logger is not None:
                self.database_logger.execute_failed(self.manager_name, query, exc)
            raise

        if self.database_logger is not None:
            self.database_logger.execute_succeeded(self.manager_name, query)

    def _clear_runtime_dependencies(self) -> None:
        self.query_executor = None
        self.single_row_inserter = None
        self.batch_row_inserter = None
        self.fetcher = None

    @log_database_lifecycle(
        started="close_started", succeeded="close_succeeded", failed="close_failed"
    )
    def close(self) -> None:
        """Close the PostgreSQL connection."""
        try:
            self.connector.close_connection()
        finally:
            self._clear_runtime_dependencies()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: typing.Any,
    ) -> None:
        self.close()
