"""
### ETL: Operational database -> warehouse staging -> warehouse
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Iterable

from airflow.decorators import dag, task
from airflow.models.baseoperator import chain
from pendulum import datetime, duration

PROJECT_ROOT = Path("/opt/airflow/project")
if not PROJECT_ROOT.exists():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.database.managers.base import PythonDatabaseManagerLogger
from scripts.database.managers.factory import create_manager_from_env
from scripts.database.managers.postgresql import (
    PostgreSQLDatabaseManager,
    PostgreSQLDatabaseManagerContext,
)
from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.pipeline_elt import PipelineELT
from scripts.pipeline.postgres_warehouse_sink import PostgresWarehouseSink
from scripts.pipeline.sql_file_transformation import SqlFileTransformation
from scripts.pipeline.watermarked_postgres_table_source import WatermarkedPostgresTableSource


OPERATIONAL_DSN_ENV_VAR = "POSTGRES_DSN"
WAREHOUSE_DSN_ENV_VAR = "WAREHOUSE_POSTGRES_DSN"
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


def print_rows(rows: Iterable[dict[str, object]]) -> None:
    rows = [dict(row) for row in rows]
    if not rows:
        print("(no rows)")
        return

    for row in rows:
        print(row)


def fetch_warehouse_staging_counts(
    database: PostgreSQLDatabaseManager,
) -> list[dict[str, object]]:
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


operational_context = PostgreSQLDatabaseManagerContext(
    autocommit=False,
    schema_metadata_store=None,
    data_schema_cleaner=None,
    connection_kwargs={},
    database_logger=PythonDatabaseManagerLogger(
        logging.getLogger("airflow.operational_to_warehouse.OperationalDB")
    ),
)

warehouse_context = PostgreSQLDatabaseManagerContext(
    autocommit=False,
    schema_metadata_store=None,
    connection_kwargs={},
    data_schema_cleaner=None,
    database_logger=PythonDatabaseManagerLogger(
        logging.getLogger("airflow.operational_to_warehouse.WarehouseDB")
    ),
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
    warehouse_staging_sink = PostgresWarehouseSink(
        name="warehouse_staging",
        database=warehouse_database,
        setup_sql_paths=[
            sql_path("data_warehouse", "init", "01_warehouse_schema.sql"),
            sql_path("data_warehouse", "init", "03_staging_schema.sql"),
        ],
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


def run_operational_to_warehouse_once() -> None:
    with (
        create_manager_from_env(
            "pg",
            operational_context,
            OPERATIONAL_DSN_ENV_VAR,
        ) as operational_database,
        create_manager_from_env(
            "pg",
            warehouse_context,
            WAREHOUSE_DSN_ENV_VAR,
        ) as warehouse_database,
    ):
        create_operational_to_warehouse_pipeline(
            operational_database=operational_database,
            warehouse_database=warehouse_database,
        ).run()

        print("\n=== warehouse staging table counts ===")
        print_rows(fetch_warehouse_staging_counts(warehouse_database))

        print("\n=== warehouse table counts ===")
        print_rows(fetch_warehouse_counts(warehouse_database))


@dag(
    dag_display_name="Operational database to warehouse",
    dag_id="operational_to_warehouse",
    start_date=datetime(2026, 1, 1, tz="Europe/Warsaw"),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "Data team",
        "retries": 3,
        "retry_delay": duration(minutes=1),
    },
    doc_md=__doc__,
    description="ETL",
    tags=["weather", "warehouse"],
)
def operational_to_warehouse():
    @task
    def run_operational_to_warehouse_pipeline() -> None:
        """Run operational model -> stg.* -> dw.*."""
        run_operational_to_warehouse_once()

    @task
    def show_warehouse_pipeline_database_state() -> None:
        """Print operational, warehouse staging, and warehouse row counts."""
        with (
            create_manager_from_env(
                "pg",
                operational_context,
                OPERATIONAL_DSN_ENV_VAR,
            ) as operational_database,
            create_manager_from_env(
                "pg",
                warehouse_context,
                WAREHOUSE_DSN_ENV_VAR,
            ) as warehouse_database,
        ):
            print("\n=== operational model table counts ===")
            print_rows(fetch_operational_counts(operational_database))

            print("\n=== warehouse staging table counts ===")
            print_rows(fetch_warehouse_staging_counts(warehouse_database))

            print("\n=== warehouse table counts ===")
            print_rows(fetch_warehouse_counts(warehouse_database))

    chain(run_operational_to_warehouse_pipeline(), show_warehouse_pipeline_database_state())


operational_to_warehouse()
