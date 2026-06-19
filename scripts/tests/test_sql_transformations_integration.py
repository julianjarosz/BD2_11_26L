from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

try:
    import psycopg
    from psycopg.rows import dict_row
except ModuleNotFoundError:
    psycopg = None
    dict_row = None

try:
    from testcontainers.postgres import PostgresContainer
except ModuleNotFoundError:
    PostgresContainer = None

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def postgres_dsn() -> str:
    if psycopg is None or PostgresContainer is None:
        pytest.skip("psycopg and testcontainers[postgres] are required for SQL integration tests")

    container = PostgresContainer("postgres:16-alpine")
    try:
        container.start()
    except Exception as exc:  # pragma: no cover - depends on local Docker availability
        pytest.skip(f"PostgreSQL testcontainer is not available: {exc}")

    try:
        yield _psycopg_dsn(container.get_connection_url())
    finally:
        container.stop()


def _psycopg_dsn(connection_url: str) -> str:
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://"):
        if connection_url.startswith(prefix):
            return "postgresql://" + connection_url[len(prefix) :]
    return connection_url


def _run_sql_file(conn: Any, relative_path: str) -> None:
    sql = (ROOT / relative_path).read_text(encoding="utf-8")
    with conn.cursor() as cursor:
        cursor.execute(sql)
    conn.commit()


def _fetch_one(conn: Any, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        row = cursor.fetchone()
    assert row is not None
    return dict(row)


def _fetch_value(conn: Any, query: str, params: tuple[Any, ...] = ()) -> Any:
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        row = cursor.fetchone()
    assert row is not None
    return row[0]


def _insert_mapped_buffer_row(
    conn: Any,
    *,
    fetched_at: str,
    current_temp: str,
    current_condition_description: str,
    alert_description: str,
) -> None:
    columns = [
        "fetched_at",
        "location_city_name",
        "location_country_code",
        "location_lat",
        "location_lon",
        "location_timezone",
        "location_timezone_offset",
        "current_observed_at",
        "current_temp",
        "current_openweather_weather_id",
        "current_condition_main",
        "current_condition_description",
        "current_condition_icon",
        "daily_forecast_date",
        "daily_retrieved_at",
        "daily_temp_day",
        "daily_openweather_weather_id",
        "daily_condition_main",
        "daily_condition_description",
        "daily_condition_icon",
        "hourly_forecast_for",
        "hourly_retrieved_at",
        "hourly_temp",
        "hourly_openweather_weather_id",
        "hourly_condition_main",
        "hourly_condition_description",
        "hourly_condition_icon",
        "minutely_forecast_for",
        "minutely_retrieved_at",
        "minutely_precipitation",
        "air_observed_at",
        "air_aqi",
        "air_co",
        "alert_sender_name",
        "alert_event",
        "alert_start_at",
        "alert_end_at",
        "alert_description",
        "alert_tags",
    ]
    values = [
        fetched_at,
        "Warsaw",
        "PL",
        Decimal("52.22970"),
        Decimal("21.01220"),
        "Europe/Warsaw",
        3600,
        "2026-01-02 10:15:30+00",
        Decimal(current_temp),
        800,
        "Clear",
        current_condition_description,
        "01d",
        "2026-01-03",
        "2026-01-02 09:00:00+00",
        Decimal("16.00"),
        801,
        "Clouds",
        "few clouds",
        "02d",
        "2026-01-02 11:00:00+00",
        "2026-01-02 09:00:00+00",
        Decimal("14.00"),
        802,
        "Rain",
        "light rain",
        "10d",
        "2026-01-02 10:16:00+00",
        "2026-01-02 09:00:00+00",
        Decimal("0.20"),
        "2026-01-02 10:15:30+00",
        2,
        Decimal("110.00"),
        "IMGW",
        "Wind",
        "2026-01-02 11:00:00+00",
        "2026-01-02 12:00:00+00",
        alert_description,
        "wind,warning",
    ]
    placeholders = ", ".join(["%s"] * len(columns))
    column_list = ", ".join(columns)
    with conn.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO mapped_data_buffer ({column_list}) VALUES ({placeholders})",
            values,
        )


@pytest.mark.integration
def test_mapped_buffer_transformation_loads_operational_model(postgres_dsn: str) -> None:
    assert psycopg is not None
    with psycopg.connect(postgres_dsn) as conn:
        _run_sql_file(conn, "operational_database/init/01_weather_model.sql")
        _run_sql_file(conn, "operational_database/init/02_migrate_weather_condition_keys.sql")
        _run_sql_file(conn, "operational_database/init/03_mapped_raw_data_buffer.sql")

        _insert_mapped_buffer_row(
            conn,
            fetched_at="2026-01-02 09:00:00+00",
            current_temp="12.34",
            current_condition_description="clear sky old",
            alert_description="old alert payload",
        )
        _insert_mapped_buffer_row(
            conn,
            fetched_at="2026-01-02 09:05:00+00",
            current_temp="15.50",
            current_condition_description="clear sky latest",
            alert_description="latest alert payload",
        )
        conn.commit()

        _run_sql_file(
            conn,
            "operational_database/transformations/01_mapped_buffer_to_weather_model.sql",
        )

        assert _fetch_value(conn, "SELECT count(*) FROM location") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM weather_condition") == 3
        assert _fetch_value(conn, "SELECT count(*) FROM current_weather") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM daily_forecast") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM hourly_forecast") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM minutely_forecast") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM air_pollution") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM weather_alert") == 1

        location = _fetch_one(conn, "SELECT city_name, country_code, lat, lon FROM location")
        assert location == {
            "city_name": "Warsaw",
            "country_code": "PL",
            "lat": Decimal("52.22970"),
            "lon": Decimal("21.01220"),
        }

        current_weather = _fetch_one(
            conn,
            """
            SELECT temp, openweather_weather_id
            FROM current_weather
            WHERE observed_at = '2026-01-02 10:15:30+00'
            """,
        )
        assert current_weather == {"temp": Decimal("15.50"), "openweather_weather_id": 800}

        current_condition = _fetch_one(
            conn,
            """
            SELECT main, description, icon
            FROM weather_condition
            WHERE openweather_weather_id = 800
            """,
        )
        assert current_condition == {
            "main": "Clear",
            "description": "clear sky latest",
            "icon": "01d",
        }

        weather_alert = _fetch_one(
            conn,
            "SELECT event, description, tags FROM weather_alert WHERE event = 'Wind'",
        )
        assert weather_alert == {
            "event": "Wind",
            "description": "latest alert payload",
            "tags": "wind,warning",
        }

def _seed_warehouse_staging(conn: Any) -> None:
    statements = [
        (
            """
            INSERT INTO stg.location (
                location_id, city_name, country_code, lat, lon, timezone, timezone_offset
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (1, "Warsaw", "PL", Decimal("52.22970"), Decimal("21.01220"), "Europe/Warsaw", 3600),
        ),
        (
            """
            INSERT INTO stg.weather_condition (
                openweather_weather_id, main, description, icon
            ) VALUES (%s, %s, %s, %s)
            """,
            (800, "Clear", "clear sky", "01d"),
        ),
        (
            """
            INSERT INTO stg.current_weather (
                current_weather_id, location_id, openweather_weather_id, observed_at,
                temp, feels_like, pressure, humidity, dew_point, uvi, clouds, visibility,
                wind_speed, wind_deg, wind_gust, rain_1h, snow_1h
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                10,
                1,
                800,
                "2026-01-02 10:15:30+00",
                Decimal("15.50"),
                Decimal("14.80"),
                1012,
                80,
                Decimal("6.25"),
                Decimal("1.20"),
                30,
                10000,
                Decimal("4.20"),
                180,
                Decimal("5.10"),
                Decimal("0.00"),
                Decimal("0.00"),
            ),
        ),
        (
            """
            INSERT INTO stg.hourly_forecast (
                hourly_forecast_id, location_id, openweather_weather_id, forecast_for,
                retrieved_at, temp, feels_like, pressure, humidity, dew_point, uvi,
                clouds, visibility, pop, wind_speed, wind_deg, wind_gust, rain_1h, snow_1h
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                20,
                1,
                800,
                "2026-01-02 10:00:00+00",
                "2026-01-02 09:00:00+00",
                Decimal("13.00"),
                Decimal("12.80"),
                1011,
                78,
                Decimal("5.90"),
                Decimal("1.10"),
                35,
                10000,
                Decimal("0.200"),
                Decimal("4.00"),
                185,
                Decimal("5.00"),
                Decimal("0.00"),
                Decimal("0.00"),
            ),
        ),
        (
            """
            INSERT INTO stg.daily_forecast (
                daily_forecast_id, location_id, openweather_weather_id, forecast_date,
                retrieved_at, temp_day, temp_min, temp_max, pressure, humidity, dew_point,
                clouds, pop, rain, snow, wind_speed, wind_deg, wind_gust, uvi
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                30,
                1,
                800,
                "2026-01-02",
                "2026-01-02 09:00:00+00",
                Decimal("16.00"),
                Decimal("10.00"),
                Decimal("17.00"),
                1010,
                75,
                Decimal("5.50"),
                40,
                Decimal("0.100"),
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("3.50"),
                170,
                Decimal("4.20"),
                Decimal("1.50"),
            ),
        ),
        (
            """
            INSERT INTO stg.minutely_forecast (
                minutely_forecast_id, location_id, forecast_for, retrieved_at, precipitation
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (40, 1, "2026-01-02 10:16:00+00", "2026-01-02 09:00:00+00", Decimal("0.20")),
        ),
        (
            """
            INSERT INTO stg.air_pollution (
                air_pollution_id, location_id, observed_at, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                50,
                1,
                "2026-01-02 10:15:30+00",
                2,
                Decimal("110.00"),
                Decimal("1.00"),
                Decimal("2.00"),
                Decimal("3.00"),
                Decimal("4.00"),
                Decimal("5.00"),
                Decimal("6.00"),
                Decimal("7.00"),
            ),
        ),
        (
            """
            INSERT INTO stg.weather_alert (
                weather_alert_id, location_id, sender_name, event, start_at, end_at, description, tags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                60,
                1,
                "IMGW",
                "Wind",
                "2026-01-02 11:00:00+00",
                "2026-01-02 12:00:00+00",
                "Wind warning",
                "wind,warning",
            ),
        ),
    ]

    with conn.cursor() as cursor:
        for query, params in statements:
            cursor.execute(query, params)
    conn.commit()


@pytest.mark.integration
def test_warehouse_transformation_loads_dimensions_facts_and_watermarks(postgres_dsn: str) -> None:
    assert psycopg is not None
    with psycopg.connect(postgres_dsn) as conn:
        _run_sql_file(conn, "data_warehouse/init/01_warehouse_schema.sql")
        _run_sql_file(conn, "data_warehouse/init/03_staging_schema.sql")
        _seed_warehouse_staging(conn)

        _run_sql_file(conn, "data_warehouse/transformations/01_load_weather_dw.sql")

        assert _fetch_value(conn, "SELECT count(*) FROM dw.dim_date") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.dim_time") == 5
        assert _fetch_value(conn, "SELECT count(*) FROM dw.dim_location") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.dim_weather_condition") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.fact_current_weather") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.fact_hourly_forecast") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.fact_daily_forecast") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.fact_minutely_forecast") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.fact_air_pollution") == 1
        assert _fetch_value(conn, "SELECT count(*) FROM dw.fact_weather_alert") == 1

        date_dimension = _fetch_one(conn, "SELECT date_key, full_date, is_weekend FROM dw.dim_date")
        assert date_dimension["date_key"] == 20260102
        assert date_dimension["full_date"].isoformat() == "2026-01-02"
        assert date_dimension["is_weekend"] is False

        morning_time = _fetch_one(
            conn,
            "SELECT time_key, part_of_the_day FROM dw.dim_time WHERE time_key = 101530",
        )
        assert morning_time == {"time_key": 101530, "part_of_the_day": "morning"}

        current_fact = _fetch_one(
            conn,
            """
            SELECT source_buffer_id, observed_date_key, observed_time_key, temp, humidity
            FROM dw.fact_current_weather
            """,
        )
        assert current_fact == {
            "source_buffer_id": 10,
            "observed_date_key": 20260102,
            "observed_time_key": 101530,
            "temp": Decimal("15.50"),
            "humidity": 80,
        }

        accuracy_fact = _fetch_one(
            conn,
            """
            SELECT forecast_temp, actual_temp, temp_error, abs_temp_error
            FROM dw.fact_forecast_accuracy
            """,
        )
        assert accuracy_fact == {
            "forecast_temp": Decimal("13.00"),
            "actual_temp": Decimal("15.50"),
            "temp_error": Decimal("2.50"),
            "abs_temp_error": Decimal("2.50"),
        }

        weather_alert = _fetch_one(
            conn,
            "SELECT source_buffer_id, event, alert_count FROM dw.fact_weather_alert",
        )
        assert weather_alert == {"source_buffer_id": 60, "event": "Wind", "alert_count": 1}

        assert _fetch_value(
            conn,
            "SELECT last_loaded_id FROM dw.etl_watermark WHERE source_name = %s",
            ("operational.location",),
        ) == 1
        assert _fetch_value(
            conn,
            "SELECT last_loaded_id FROM dw.etl_watermark WHERE source_name = %s",
            ("operational.current_weather",),
        ) == 10
        assert _fetch_value(
            conn,
            "SELECT last_loaded_id FROM dw.etl_watermark WHERE source_name = %s",
            ("operational.weather_alert",),
        ) == 60
