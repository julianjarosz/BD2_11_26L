from typing import Any

import psycopg
from psycopg import Connection
from psycopg import sql
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

        self.successful_rows: list[DatabaseRow] = []
        self.failed_rows: list[FailedRow] = []

    def _clean_buffers(self) -> None:
        self.successful_rows.clear()
        self.failed_rows.clear()

    def _build_result(self) -> DatabaseOperationResult:
        return DatabaseOperationResult(
            successful_rows=self.successful_rows, failed_rows=self.failed_rows
        )

    def _prepare_insert_items(self, table_name: str, data: list[DatabaseRow]) -> list[tuple]:
        query_builder = self.builder_t(table_name=table_name, data=data)

        query = query_builder.get_query()
        params = query_builder.get_params()

        if isinstance(query, dict) and isinstance(params, dict):
            grouped_rows = query_builder.get_grouped_rows_by_columns()

            return [
                (query[columns], params[columns], grouped_rows[columns])
                for columns in query
            ]

        return [(query, params, data)]

    def insert(self, table_name: str, rows: list[DatabaseRow]) -> DatabaseOperationResult:
        self._clean_buffers()
        if not rows:
            return self._build_result()
        query_params_row_collection: list[tuple] = self._prepare_insert_items(table_name=table_name, data=rows)

        with self.connection.cursor() as conn_cursor:

            for query, params, grouped_rows in query_params_row_collection:
                try:
                    conn_cursor.execute(query, params)
                    if not self.autocommit:
                        self.connection.commit()
                    self.successful_rows.extend(grouped_rows)

                except Exception as error:
                    if not self.autocommit:
                        self.connection.rollback()
                    self.failed_rows.extend(
                        FailedRow(
                            table_name=table_name,
                            row=row,
                            message="Row failed during insertion",
                            exception=error
                        )
                        for row in grouped_rows
                    )

        return self._build_result()
