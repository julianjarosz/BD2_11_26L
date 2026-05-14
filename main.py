"""Run the OpenWeather-to-PostgreSQL ELT pipeline."""

from __future__ import annotations

import logging
import time

from scripts.api.weather_api_fetch import DEFAULT_CITY
from scripts.database.postgresql_database_manager import (
    PostgreSQLDatabaseManager,
    PostgreSQLDatabaseManagerContext,
)
from scripts.pipeline.api_source import OpenWeatherApiSource
from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.pipeline_elt import PipelineELT, PipelineResult
from scripts.pipeline.postgres_warehouse_sink import PostgresWarehouseSink
from scripts.utils import fetch_config_value

FETCH_INTERVAL_SECONDS = float(
    fetch_config_value("consts.conf", "openweather.fetch_interval_seconds")
)
OPENWEATHER_SOURCE_NAME = "openweather"
POSTGRES_SINK_NAME = "postgres_warehouse"
RAW_WEATHER_TABLE = "data_buffer"


def create_postgres_manager() -> PostgreSQLDatabaseManager:
    """Create a PostgreSQL manager for the pipeline warehouse sink."""
    logger = logging.getLogger(__name__)
    context = PostgreSQLDatabaseManagerContext(
        autocommit=False,
        schema_metadata_store=None,
        logger=logger,
        connection_kwargs={},
    )
    return PostgreSQLDatabaseManager.create_from_env(context)


def create_weather_pipeline(
    database: PostgreSQLDatabaseManager,
    city: str = DEFAULT_CITY,
) -> PipelineELT:
    """Create the OpenWeather ELT pipeline.

    Args:
        database: PostgreSQL database manager used by the warehouse sink.
        city: City name fetched from OpenWeather.

    Returns:
        Configured pipeline that extracts one OpenWeather row and loads it into
        the raw weather table.
    """
    source = OpenWeatherApiSource(name=OPENWEATHER_SOURCE_NAME)
    sink = PostgresWarehouseSink(
        name=POSTGRES_SINK_NAME,
        database=database,
        transformations=[],
    )
    load_step = LoadStep(
        source_name=OPENWEATHER_SOURCE_NAME,
        source_resource=city,
        sink_name=POSTGRES_SINK_NAME,
        staging_table=RAW_WEATHER_TABLE,
    )
    return PipelineELT(
        sources=[source],
        sinks=[sink],
        load_steps=[load_step],
    )


def run_weather_pipeline_once(city: str = DEFAULT_CITY) -> PipelineResult:
    """Run one OpenWeather ingestion pass.

    Args:
        city: City name fetched from OpenWeather.

    Returns:
        Summary of the pipeline run.
    """
    database = create_postgres_manager()
    pipeline = create_weather_pipeline(database, city)
    try:
        return pipeline.run()
    finally:
        database.close()
        for source in pipeline.sources.values():
            close = getattr(source, "close", None)
            if close is not None:
                close()


def run_weather_pipeline_forever(
    city: str = DEFAULT_CITY,
    interval_seconds: float = FETCH_INTERVAL_SECONDS,
) -> None:
    """Run the OpenWeather ingestion pipeline continuously."""
    logger = logging.getLogger(__name__)
    while True:
        try:
            result = run_weather_pipeline_once(city)
            logger.info("Weather pipeline result: %s", result)
        except Exception:
            logger.exception("Weather pipeline pass failed.")

        time.sleep(interval_seconds)


def main() -> None:
    """Run weather ingestion continuously."""
    logging.basicConfig(level=logging.INFO)
    try:
        run_weather_pipeline_forever()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Weather ingestion stopped.")


if __name__ == "__main__":
    main()
