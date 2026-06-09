"""
### ETL: API -> operational staging -> operational database
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

from scripts.api.openweather_manager import DEFAULT_CITY_NAMES
from scripts.database.managers.base import PythonDatabaseManagerLogger
from scripts.database.managers.factory import create_manager_from_env
from scripts.database.managers.postgresql import (
    PostgreSQLDatabaseManager,
    PostgreSQLDatabaseManagerContext,
)
from scripts.pipeline.api_source import OpenWeatherApiSource
from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.pipeline_elt import PipelineELT
from scripts.pipeline.postgres_warehouse_sink import PostgresWarehouseSink
from scripts.pipeline.sql_file_transformation import SqlFileTransformation


OPERATIONAL_DSN_ENV_VAR = "POSTGRES_DSN"
OPERATIONAL_STAGING_TABLE = "mapped_data_buffer"
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


def sql_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def print_rows(rows: Iterable[dict[str, object]]) -> None:
    rows = [dict(row) for row in rows]
    if not rows:
        print("(no rows)")
        return

    for row in rows:
        print(row)


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
        logging.getLogger("airflow.api_to_operational.OperationalDB")
    ),
)


def create_api_to_operational_pipeline(
    operational_database: PostgreSQLDatabaseManager,
    cities: Iterable[str] = DEFAULT_CITY_NAMES,
) -> PipelineELT:
    operational_staging_sink = PostgresWarehouseSink(
        name="operational_staging",
        database=operational_database,
        setup_sql_paths=[
            sql_path("operational_database", "init", "01_weather_model.sql"),
            sql_path("operational_database", "init", "02_migrate_weather_condition_keys.sql"),
            sql_path("operational_database", "init", "03_mapped_raw_data_buffer.sql"),
        ],
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


def run_api_to_operational_once(cities: Iterable[str] = DEFAULT_CITY_NAMES) -> None:
    with create_manager_from_env(
        "pg",
        operational_context,
        OPERATIONAL_DSN_ENV_VAR,
    ) as operational_database:
        create_api_to_operational_pipeline(
            operational_database=operational_database,
            cities=cities,
        ).run()

        print("\n=== operational model table counts ===")
        print_rows(fetch_operational_counts(operational_database))


@dag(
    dag_display_name="API to operational database",
    dag_id="api_to_operational",
    start_date=datetime(2026, 1, 1, tz="Europe/Warsaw"),
    schedule="*/2 * * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "Data team",
        "retries": 3,
        "retry_delay": duration(minutes=1),
    },
    doc_md=__doc__,
    description="ETL",
    tags=["weather", "api", "operational"],
)
def api_to_operational():
    @task
    def run_api_to_operational_pipeline() -> None:
        """Run API -> mapped_data_buffer -> operational model."""
        run_api_to_operational_once()

    @task
    def show_operational_database_state() -> None:
        """Print operational staging and model table row counts."""
        with create_manager_from_env(
            "pg",
            operational_context,
            OPERATIONAL_DSN_ENV_VAR,
        ) as operational_database:
            staging_count = operational_database.fetch_data(
                f"SELECT count(*) AS row_count FROM {OPERATIONAL_STAGING_TABLE}"
            )

            print("\n=== operational staging table counts ===")
            print_rows(
                [
                    {
                        "table": OPERATIONAL_STAGING_TABLE,
                        "rows": staging_count.successful_rows[0]["row_count"],
                    }
                ]
            )

            print("\n=== operational model table counts ===")
            print_rows(fetch_operational_counts(operational_database))

    chain(run_api_to_operational_pipeline(), show_operational_database_state())


api_to_operational()
