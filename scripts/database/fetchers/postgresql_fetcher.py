"""PostgreSQL data fetching."""

from __future__ import annotations

from typing import cast
from logging import Logger
from psycopg import sql
import psycopg

from scripts.database.executors.postgresql_query_executor import PostgreSQLQueryExecutor
from scripts.database.fetchers.base_fetcher import BaseFetcher
from scripts.database.models.database_types import DatabaseOperationResult, DatabaseParams, DatabaseRow
from scripts.database.models.query import Query


class PostgreSQLCursorFetchCallback:
    def __init__(self, logger: Logger | None = None) -> None:
        self.cb_logger: Logger | None = logger

    def __call__(self, cursor: psycopg.cursor.Cursor) -> list[DatabaseRow] | None:
        try:
            result = [cast(DatabaseRow, row) for row in cursor.fetchall()]
            if self.cb_logger is not None:
                self.cb_logger.info("Fetched %s rows", len(result))
            return result
        except psycopg.ProgrammingError:
            if self.cb_logger is not None:
                self.cb_logger.exception("cursor.fetchall() failed to fetch all rows\n")
            raise


class PostgreSQLDatabaseFetcher(BaseFetcher[Query | str | sql.Composed, DatabaseParams | None]):
    def __init__(
        self, query_executor: PostgreSQLQueryExecutor, logger: Logger | None = None
    ) -> None:
        self.query_executor: PostgreSQLQueryExecutor = query_executor
        self.logger: Logger | None = logger

    def fetch(
        self, query: Query | str | sql.Composed, params: DatabaseParams | None = None
    ) -> DatabaseOperationResult:
        fetched_rows: list[DatabaseRow] | None = self.query_executor.execute(
            query=query,
            params=params,
            cursor_callback=PostgreSQLCursorFetchCallback(self.logger),
        )

        return DatabaseOperationResult(successful_rows=fetched_rows, failed_rows=[])
