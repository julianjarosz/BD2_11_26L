"""Run API -> operational staging -> warehouse staging and print the result."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

from scripts.api.openweather_manager import DEFAULT_CITY_NAMES
from scripts.database.managers.base import PythonDatabaseManagerLogger
from scripts.database.managers.postgresql import (
    PostgreSQLDatabaseManager,
    PostgreSQLDatabaseManagerContext,
)
from scripts.database.managers.factory import create_manager_from_env
from scripts.pipeline.api_source import OpenWeatherApiSource
from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.pipeline_elt import PipelineELT
from scripts.pipeline.postgres_warehouse_sink import PostgresWarehouseSink
from scripts.pipeline.sql_file_transformation import SqlFileTransformation
from scripts.pipeline.watermarked_postgres_table_source import WatermarkedPostgresTableSource

PROJECT_ROOT = Path(__file__).resolve().parent

OPERATIONAL_DSN_ENV_VAR = "POSTGRES_DSN"
WAREHOUSE_DSN_ENV_VAR = "WAREHOUSE_POSTGRES_DSN"

OPERATIONAL_STAGING_TABLE = "mapped_data_buffer"
OPERATIONAL_TO_WAREHOUSE_TABLES = (
    ("location", "location_id", "stg.location"),
    ("weather_condition", "openweather_weather_id", "stg.weather_condition"),
    ("current_weather", "current_weather_id", "stg.current_weather"),
    ("hourly_forecast", "hourly_forecast_id", "stg.hourly_forecast"),
    ("daily_forecast", "daily_forecast_id", "stg.daily_forecast"),
    ("minutely_forecast", "minutely_forecast_id", "stg.minutely_forecast"),
    ("air_pollution", "air_pollution_id", "stg.air_pollution"),
    ("weather_alert", "weather_alert_id", "stg.weather_alert"),
)

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

def create_api_to_operational_pipeline(
    operational_database: PostgreSQLDatabaseManager,
    cities: Iterable[str] = DEFAULT_CITY_NAMES,
) -> PipelineELT:
    operational_staging_sink = staging_sink(
        name="operational_staging",
        database=operational_database,
        setup_sql=(
            ("operational_database", "init", "01_weather_model.sql"),
            ("operational_database", "init", "02_migrate_weather_condition_keys.sql"),
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

    return PipelineELT(
        load_steps=[
            LoadStep(
                source=OpenWeatherApiSource("openweather_api"),
                source_resource=city,
                sink=operational_staging_sink,
                staging_table=OPERATIONAL_STAGING_TABLE,
            )
            for city in cities
        ]
    )


def create_operational_to_warehouse_pipeline(
    operational_database: PostgreSQLDatabaseManager,
    warehouse_database: PostgreSQLDatabaseManager,
) -> PipelineELT:
    operational_source = WatermarkedPostgresTableSource(
        name="operational_model",
        operational_database=operational_database,
        warehouse_database=warehouse_database,
        id_columns={
            table_name: id_column
            for table_name, id_column, _staging_table in OPERATIONAL_TO_WAREHOUSE_TABLES
        },
        full_load_tables={"location", "weather_condition"},
    )
    warehouse_staging_sink = staging_sink(
        name="warehouse_staging",
        database=warehouse_database,
        setup_sql=(
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
                source=operational_source,
                source_resource=table_name,
                sink=warehouse_staging_sink,
                staging_table=staging_table,
            )
            for table_name, _id_column, staging_table in OPERATIONAL_TO_WAREHOUSE_TABLES
        ]
    )


def create_api_to_warehouse_staging_pipeline(
    operational_database: PostgreSQLDatabaseManager,
    warehouse_database: PostgreSQLDatabaseManager,
    cities: Iterable[str] = DEFAULT_CITY_NAMES,
) -> PipelineELT:
    return PipelineELT(
        load_steps=[
            *create_api_to_operational_pipeline(
                operational_database=operational_database,
                cities=cities,
            ).load_steps,
            *create_operational_to_warehouse_pipeline(
                operational_database=operational_database,
                warehouse_database=warehouse_database,
            ).load_steps,
        ]
    )

def fetch_warehouse_staging_counts(database: PostgreSQLDatabaseManager) -> list[dict[str, object]]:
    rows = []
    for _table_name, _id_column, staging_table in OPERATIONAL_TO_WAREHOUSE_TABLES:
        result = database.fetch_data(f"SELECT count(*) AS row_count FROM {staging_table}")
        rows.append({"table": staging_table, "rows": result.successful_rows[0]["row_count"]})
    return rows

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

operational_context = PostgreSQLDatabaseManagerContext(
        autocommit=False,
        schema_metadata_store=None,
        data_schema_cleaner=None,
        connection_kwargs={},
        database_logger=PythonDatabaseManagerLogger(logging.getLogger(f"{__name__}.OperationalDB")),
)

warehouse_context = PostgreSQLDatabaseManagerContext(
    autocommit=False,
    schema_metadata_store=None,
    connection_kwargs={},
    data_schema_cleaner=None,
    database_logger=PythonDatabaseManagerLogger(logging.getLogger(f"{__name__}.WarehouseDB")),
)

def run_api_to_operational_once(cities: Iterable[str] = DEFAULT_CITY_NAMES) -> None:
    with create_manager_from_env("pg", operational_context, OPERATIONAL_DSN_ENV_VAR) as operational_database:
        create_api_to_operational_pipeline(
            operational_database=operational_database,
            cities=cities,
        ).run()

        print("\n=== operational model table counts ===")
        print_rows(fetch_operational_counts(operational_database))


def run_operational_to_warehouse_once() -> None:
    with (
        create_manager_from_env("pg", operational_context, OPERATIONAL_DSN_ENV_VAR) as operational_database,
        create_manager_from_env("pg", warehouse_context, WAREHOUSE_DSN_ENV_VAR) as warehouse_database,
    ):
        create_operational_to_warehouse_pipeline(
            operational_database=operational_database,
            warehouse_database=warehouse_database,
        ).run()

        print("\n=== warehouse staging table counts ===")
        print_rows(fetch_warehouse_staging_counts(warehouse_database))

        print("\n=== warehouse table counts ===")
        print_rows(fetch_warehouse_counts(warehouse_database))


def run_api_to_warehouse_staging_once(cities: Iterable[str] = DEFAULT_CITY_NAMES) -> None:
    run_api_to_operational_once(cities)
    run_operational_to_warehouse_once()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "WARNING").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    pipeline_mode = os.getenv("PIPELINE_MODE", "all").lower()
    if pipeline_mode == "api_to_operational":
        run_api_to_operational_once()
    elif pipeline_mode == "operational_to_warehouse":
        run_operational_to_warehouse_once()
    elif pipeline_mode == "all":
        run_api_to_warehouse_staging_once()
    else:
        raise ValueError("Invalid PIPELINE_MODE")

if __name__ == "__main__":
    main()
