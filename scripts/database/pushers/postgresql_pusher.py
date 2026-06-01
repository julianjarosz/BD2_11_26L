from __future__ import annotations

import typing

from scripts.database.executors.base_executor import BaseExecutor
from scripts.database.models.database_types import DatabaseRow, DatabaseOperationResult, FailedRow
from scripts.database.builders.base_query_builder import BaseQueryBuilder
from scripts.database.pushers.base_pusher import BasePusher


class PostgreSQLDatabasePusher(BasePusher):

    def __init__(
        self,
        query_executor: BaseExecutor[typing.Any, typing.Any],
        builder_t: type[BaseQueryBuilder],
    ) -> None:
        super().__init__(query_executor, builder_t)

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
        if self.builder_t.__name__ == "SingleRowInsertQueryBuilder":
            insert_items: list[tuple] = []
            for row in data:
                query_builder = self.builder_t(table_name=table_name, data=row)
                insert_items.append((query_builder.get_query(), query_builder.get_params(), [row]))
            return insert_items

        query_builder = self.builder_t(table_name=table_name, data=data)

        query = query_builder.get_query()
        params = query_builder.get_params()

        if isinstance(query, dict) and isinstance(params, dict):
            grouped_rows = query_builder.get_grouped_rows_by_columns()

            return [(query[columns], params[columns], grouped_rows[columns]) for columns in query]

        return [(query, params, data)]

    def insert(self, table_name: str, rows: list[DatabaseRow]) -> DatabaseOperationResult:
        self._clean_buffers()
        if not rows:
            return self._build_result()
        query_params_row_collection: list[tuple] = self._prepare_insert_items(
            table_name=table_name,
            data=rows,
        )

        for query, params, grouped_rows in query_params_row_collection:
            try:
                self.query_executor.execute(query, params)
                self.successful_rows.extend(grouped_rows)

            except Exception as error:
                self.failed_rows.extend(
                    FailedRow(
                        table_name=table_name,
                        row=row,
                        message="Row failed during insertion",
                        exception=error,
                    )
                    for row in grouped_rows
                )

        return self._build_result()
