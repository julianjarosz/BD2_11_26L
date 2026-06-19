from __future__ import annotations

from typing import Any

import pytest

from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import (
    DatabaseOperationResult,
    DatabaseRequestType,
    FailedRow,
)
from scripts.errors.pipeline_errors import PostgresWarehouseSinkError
from scripts.pipeline.postgres_warehouse_sink import PostgresWarehouseSink


class RecordingDatabase:
    def __init__(
        self,
        push_result: DatabaseOperationResult | None = None,
        push_error: Exception | None = None,
    ) -> None:
        self.executed: list[str] = []
        self.push_calls: list[tuple[str, DatabasePayload]] = []
        self.push_result = push_result or DatabaseOperationResult(
            successful_rows=[],
            failed_rows=[],
        )
        self.push_error = push_error

    def execute(self, query: str, **_kwargs: Any) -> None:
        self.executed.append(query)

    def push_data(
        self, table_name: str, data: DatabasePayload, **_kwargs: Any
    ) -> DatabaseOperationResult:
        self.push_calls.append((table_name, data))
        if self.push_error is not None:
            raise self.push_error
        return self.push_result


def test_clear_staging_runs_setup_sql_before_truncate(tmp_path: Any) -> None:
    setup_sql = tmp_path / "setup.sql"
    setup_sql.write_text("CREATE SCHEMA IF NOT EXISTS stg;", encoding="utf-8")
    database = RecordingDatabase()
    sink = PostgresWarehouseSink(
        name="warehouse",
        database=database,  # type: ignore[arg-type]
        transformations=[],
        setup_sql_paths=[setup_sql],
    )

    sink.clear_staging("stg.weather")

    assert database.executed == [
        "CREATE SCHEMA IF NOT EXISTS stg;",
        "TRUNCATE TABLE stg.weather RESTART IDENTITY",
    ]


def test_load_staging_returns_zero_without_pushing_empty_rows() -> None:
    database = RecordingDatabase()
    sink = PostgresWarehouseSink(
        name="warehouse",
        database=database,  # type: ignore[arg-type]
        transformations=[],
    )

    assert sink.load_staging("stg.weather", []) == 0
    assert database.push_calls == []


def test_load_staging_builds_insert_payload_and_returns_success_count() -> None:
    rows = [{"id": 1, "temp": 12.5}, {"id": 2, "temp": 13.5}]
    database = RecordingDatabase(
        push_result=DatabaseOperationResult(
            successful_rows=rows,
            failed_rows=[],
        )
    )
    sink = PostgresWarehouseSink(
        name="warehouse",
        database=database,  # type: ignore[arg-type]
        transformations=[],
    )

    count = sink.load_staging("stg.weather", rows)

    assert count == 2
    assert len(database.push_calls) == 1
    table_name, payload = database.push_calls[0]
    assert table_name == "stg.weather"
    assert payload.rows == rows
    assert payload.number_of_rows == 2
    assert payload.request_type == DatabaseRequestType.INSERT_DATA


def test_load_staging_wraps_failed_push_rows() -> None:
    failed_row = FailedRow(
        table_name="stg.weather",
        row={"id": 1},
        message="failed",
        exception=RuntimeError("insert failed"),
    )
    database = RecordingDatabase(
        push_result=DatabaseOperationResult(successful_rows=[], failed_rows=[failed_row])
    )
    sink = PostgresWarehouseSink(
        name="warehouse",
        database=database,  # type: ignore[arg-type]
        transformations=[],
    )

    with pytest.raises(PostgresWarehouseSinkError, match="Failed to load staging table"):
        sink.load_staging("stg.weather", [{"id": 1}])
