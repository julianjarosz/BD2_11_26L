"""PostgreSQL implementation of the database manager interface."""

from __future__ import annotations

import dataclasses
import logging
import os
import typing

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
from scripts.errors.database_errors import CleaningException, InvalidRequestType
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

    def _insert_rows(
        self, table_name: str, payload: DatabasePayload
    ) -> DatabaseOperationResult: ...
        # TODO - create insertion script for database payload

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
        
        insertion_result: DatabaseOperationResult = self._insert_rows(table_name, (
            cleaning_results.cleaned_payload if cleaning_results is not None else payload
        ))

        return DatabaseOperationResult(
            successful_rows=insertion_result.successful_rows,
            failed_rows=(
                insertion_result.failed_rows
                + (cleaning_results.failed_rows if cleaning_results is not None else [])
            ),
        )
        
    def fetch_data(self, query: Query | str, params: DatabaseParams | None = None) -> DatabaseOperationResult:
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

    def _log_row_group_insert(
        self,
        table_name: str,
        payload: DatabasePayload,
        columns: tuple[str, ...],
        grouped_rows: list[DatabaseRow],
    ) -> None:
        self.logger.info(
            "Inserting row group into %s: sender=%s rows=%s columns=%s",
            table_name,
            payload.sender,
            len(grouped_rows),
            columns,
        )

    def _log_payload_insert_failed(
        self, table_name: str, prepared_payload: PreparedDatabasePayload
    ) -> None:
        self.logger.exception(
            "Failed to insert database payload: sender=%s table=%s valid_rows=%s rejected_rows=%s",
            prepared_payload.payload.sender,
            table_name,
            len(prepared_payload.valid_rows),
            len(prepared_payload.rejected_rows),
        )

    def _log_payload_inserted(
        self, table_name: str, prepared_payload: PreparedDatabasePayload
    ) -> None:
        self.logger.info(
            "Inserted database payload: sender=%s table=%s inserted=%s rejected=%s",
            prepared_payload.payload.sender,
            table_name,
            len(prepared_payload.valid_rows),
            len(prepared_payload.rejected_rows),
        )

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
