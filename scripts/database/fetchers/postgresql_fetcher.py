"""PostgreSQL data fetching."""

from __future__ import annotations

from typing import Any, cast

import psycopg
from psycopg import sql

from scripts.database.executors.postgresql_query_executor import PostgreSQLQueryExecutor
from scripts.database.fetchers.base_fetcher import BaseFetcher
from scripts.database.models.database_types import (
    DatabaseOperationResult,
    DatabaseParams,
    DatabaseRow,
)
from scripts.database.models.query import Query


class PostgreSQLCursorFetchCallback:
    def __call__(self, cursor: psycopg.cursor.Cursor) -> list[DatabaseRow] | None:
        return [cast(DatabaseRow, row) for row in cursor.fetchall()]


class PostgreSQLDatabaseFetcher(BaseFetcher[Query | str | sql.Composed, DatabaseParams | None]):
    def __init__(self, query_executor: PostgreSQLQueryExecutor) -> None:
        self.query_executor: PostgreSQLQueryExecutor = query_executor

    def fetch(
        self,
        query: Query | str | sql.Composed,
        params: DatabaseParams | None = None,
        **exec_kwargs: dict[str, Any],
    ) -> DatabaseOperationResult:
        fetched_rows: list[DatabaseRow] | None = self.query_executor.execute(
            query=query,
            params=params,
            callback=PostgreSQLCursorFetchCallback(),
            **exec_kwargs,
        )

        return DatabaseOperationResult(successful_rows=fetched_rows, failed_rows=[])
