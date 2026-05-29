"""Run API -> operational staging -> warehouse staging and print the result."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

from scripts.api.openweather_manager import DEFAULT_CITY_NAME
from scripts.database.managers.postgresql_database_manager import (
    PostgreSQLDatabaseManager,
    PostgreSQLDatabaseManagerContext,
)
from scripts.pipeline.api_source import OpenWeatherApiSource
from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.pipeline_elt import PipelineELT
from scripts.pipeline.postgres_table_source import PostgresTableSource
from scripts.pipeline.postgres_warehouse_sink import PostgresWarehouseSink
from scripts.pipeline.sql_file_transformation import SqlFileTransformation

PROJECT_ROOT = Path(__file__).resolve().parent

OPERATIONAL_DSN_ENV_VAR = "POSTGRES_DSN"
WAREHOUSE_DSN_ENV_VAR = "WAREHOUSE_POSTGRES_DSN"

OPERATIONAL_STAGING_TABLE = "mapped_data_buffer"
WAREHOUSE_STAGING_TABLE = "stg.mapped_data_buffer"

OPERATIONAL_MODEL_TABLES = (
    "location",
    "weather_condition",
    "current_weather",
    "hourly_forecast",
    "daily_forecast",
    "minutely_forecast",
    "air_pollution",
    "weather_alert",
)

WAREHOUSE_TABLES = (
    "dw.dim_date",
    "dw.dim_time",
    "dw.dim_location",
    "dw.dim_weather_condition",
    "dw.fact_current_weather",
    "dw.fact_hourly_forecast",
    "dw.fact_daily_forecast",
    "dw.fact_minutely_forecast",
    "dw.fact_air_pollution",
    "dw.fact_weather_alert",
    "dw.fact_forecast_accuracy",
)


def sql_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def create_postgres_manager(env_var: str) -> PostgreSQLDatabaseManager:
    context = PostgreSQLDatabaseManagerContext(
        autocommit=False,
        schema_metadata_store=None,
        data_schema_cleaner=None,
        logger=logging.getLogger(__name__),
        connection_kwargs={},
    )
    return PostgreSQLDatabaseManager.create_from_env(context, env_var)


def staging_sink(
    name: str,
    database: PostgreSQLDatabaseManager,
    setup_sql: tuple[tuple[str, ...], ...],
    transformations: list[SqlFileTransformation] | None = None,
) -> PostgresWarehouseSink:
    return PostgresWarehouseSink(
        name=name,
        database=database,
        setup_sql_paths=[sql_path(*path_parts) for path_parts in setup_sql],
        transformations=transformations or [],
    )


def create_api_to_warehouse_staging_pipeline(
    operational_database: PostgreSQLDatabaseManager,
    warehouse_database: PostgreSQLDatabaseManager,
    city: str = DEFAULT_CITY_NAME,
) -> PipelineELT:
    operational_staging_sink = staging_sink(
        name="operational_staging",
        database=operational_database,
        setup_sql=(
            ("operational_database", "init", "01_weather_model.sql"),
            ("operational_database", "init", "03_mapped_raw_data_buffer.sql"),
        ),
        transformations=[
            SqlFileTransformation(
                name="mapped_buffer_to_operational_model",
                path=sql_path(
                    "operational_database",
                    "transformations",
                    "01_mapped_buffer_to_weather_model.sql",
                ),
            )
        ],
    )
    warehouse_staging_sink = staging_sink(
        name="warehouse_staging",
        database=warehouse_database,
        setup_sql=(
            ("data_warehouse", "init", "00_reset_warehouse_schema.sql"),
            ("data_warehouse", "init", "01_warehouse_schema.sql"),
            ("data_warehouse", "init", "03_staging_schema.sql"),
        ),
        transformations=[
            SqlFileTransformation(
                name="load_weather_dw",
                path=sql_path("data_warehouse", "transformations", "01_load_weather_dw.sql"),
            )
        ],
    )

    return PipelineELT(
        load_steps=[
            LoadStep(
                source=OpenWeatherApiSource("openweather_api"),
                source_resource=city,
                sink=operational_staging_sink,
                staging_table=OPERATIONAL_STAGING_TABLE,
            ),
            LoadStep(
                source=PostgresTableSource("operational_staging", operational_database),
                source_resource=OPERATIONAL_STAGING_TABLE,
                sink=warehouse_staging_sink,
                staging_table=WAREHOUSE_STAGING_TABLE,
            ),
        ]
    )


def fetch_warehouse_staging_preview(
    database: PostgreSQLDatabaseManager,
    limit: int = 5,
) -> list[dict[str, object]]:
    return list(
        database.fetch_data(
            f"""
            SELECT *
            FROM {WAREHOUSE_STAGING_TABLE}
            ORDER BY mapped_data_buffer_id DESC NULLS LAST
            LIMIT {limit}
            """
        ).successful_rows
    )


def fetch_warehouse_counts(database: PostgreSQLDatabaseManager) -> list[dict[str, object]]:
    rows = []
    for table_name in WAREHOUSE_TABLES:
        result = database.fetch_data(f"SELECT count(*) AS row_count FROM {table_name}")
        rows.append({"table": table_name, "rows": result.successful_rows[0]["row_count"]})
    return rows


def fetch_operational_counts(database: PostgreSQLDatabaseManager) -> list[dict[str, object]]:
    rows = []
    for table_name in OPERATIONAL_MODEL_TABLES:
        result = database.fetch_data(f"SELECT count(*) AS row_count FROM {table_name}")
        rows.append({"table": table_name, "rows": result.successful_rows[0]["row_count"]})
    return rows


def print_rows(rows: Iterable[dict[str, object]]) -> None:
    rows = [dict(row) for row in rows]
    if not rows:
        print("(no rows)")
        return

    for row in rows:
        print(row)


def run_api_to_warehouse_staging_once(city: str = DEFAULT_CITY_NAME) -> None:
    operational_database = create_postgres_manager(OPERATIONAL_DSN_ENV_VAR)
    warehouse_database = create_postgres_manager(WAREHOUSE_DSN_ENV_VAR)

    try:
        create_api_to_warehouse_staging_pipeline(
            operational_database=operational_database,
            warehouse_database=warehouse_database,
            city=city,
        ).run()

        print("\n=== operational model table counts ===")
        print_rows(fetch_operational_counts(operational_database))

        print(f"\n=== {WAREHOUSE_STAGING_TABLE} ===")
        print_rows(fetch_warehouse_staging_preview(warehouse_database))

        print("\n=== warehouse table counts ===")
        print_rows(fetch_warehouse_counts(warehouse_database))
    finally:
        operational_database.close()
        warehouse_database.close()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_api_to_warehouse_staging_once()


if __name__ == "__main__":
    main()
