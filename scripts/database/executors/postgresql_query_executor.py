"""PostgreSQL query execution primitives."""

from __future__ import annotations

from typing import Any, final

import psycopg
from psycopg import sql

from scripts.database.models.database_types import DatabaseParams
from scripts.database.models.query import Query
from scripts.database.executors.base_executor import BaseExecutor


@final
class PostgreSQLQueryExecutor(BaseExecutor[str | Query | sql.Composed], DatabaseParams | None):
    """Shared PostgreSQL connection with query execution helpers."""

    def __init__(self, db_connection: psycopg.Connection, autocommit: bool) -> None:
        self.db_connection: psycopg.Connection = db_connection
        self.autocommit: bool = autocommit

    @staticmethod
    def normalize_query(query: Query | str | sql.Composable) -> str | sql.Composable:
        return str(query) if isinstance(query, Query) else query

    def execute(
        self,
        query: Query | str | sql.Composable,
        params: DatabaseParams | None = None,
        *exec_kwargs: dict[str, Any],
    ) -> None:
        normalized_query: str | sql.Composable = PostgreSQLQueryExecutor.normalize_query(query)
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(normalized_query, params, **exec_kwargs)
            if not self.autocommit:
                self.db_connection.commit()

        except Exception:
            if not self.autocommit:
                self.db_connection.rollback()
            raise
