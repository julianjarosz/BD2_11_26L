from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from scripts.database.models.database_types import DatabaseRow, DatabaseOperationResult, FailedRow
from scripts.database.builders.base_query_builder import BaseQueryBuilder


class PostgreSQLDatabasePusher:

    def __init__(
        self, dsn: str, autocommit: bool, builder_t: type[BaseQueryBuilder], **connection_kwargs
    ) -> None:
        self.connection: Connection = psycopg.connect(
            dsn=dsn, autocommit=autocommit, row_factory=dict_row, **connection_kwargs
        )
        self.autocommit: bool = autocommit
        self.builder_t: type[BaseQueryBuilder] = builder_t

    def _prepare_query_and_params(self, table_name: str, data) -> tuple:
        query_builder = self.builder_t(table_name=table_name, data=data)
        return query_builder.get_query(), query_builder.get_params()

    def insert(self, table_name: str, rows: list[DatabaseRow]) -> DatabaseOperationResult:
        if not rows:
            return DatabaseOperationResult(successful_rows=[], failed_rows=[])
        query, params = self._prepare_query_and_params(table_name, rows)

        with self.connection.cursor() as conn_cursor:

            try:
                if isinstance(query, dict) and isinstance(params, dict):
                    for columns, insert_query in query.items():
                        conn_cursor.execute(insert_query, params[columns])
                else:
                    conn_cursor.execute(query, params)

                if not self.autocommit:
                    self.connection.commit()

                return DatabaseOperationResult(successful_rows=rows, failed_rows=[])
            except Exception as exce:
                if not self.autocommit:
                    self.connection.rollback()

                return DatabaseOperationResult(
                    successful_rows=[],
                    failed_rows=[
                        FailedRow(
                            table_name=table_name,
                            row=row,
                            message="Failed to insert row",
                            exception=exce,
                        )
                        for row in rows
                    ],
                )
