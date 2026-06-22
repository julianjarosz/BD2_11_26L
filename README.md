
# Weather Data Platform

An end-to-end weather analytics platform that collects data from OpenWeather, stores it in a normalized operational PostgreSQL database, incrementally loads a dimensional data warehouse, and exposes the resulting model to Power BI.

The project can run either as scheduled Apache Airflow workflows or as a one-shot Python pipeline. Docker Compose provides all required databases, Airflow services, pgAdmin, and the Python runtime.

The platform uses two PostgreSQL databases:

- **Operational database** — stores normalized source-level weather observations, forecasts, pollution measurements, and alerts.
- **Data warehouse** — stores analytics-ready dimensions and facts, together with ETL watermarks.

A third PostgreSQL instance stores Airflow metadata only.

## Data pipeline

### Stage 1: OpenWeather to the operational database

For each city, the pipeline:

1. Calls the OpenWeather api endpoints for current weather, daily, hourly, and minutely forecasts and weather alerts.
2. Calls the OpenWeather Air Pollution api.
3. Parses the responses and flattens one snapshot into a row.
4. Loads the row into `mapped_data_buffer`.
5. Runs `operational_database/transformations/01_mapped_buffer_to_weather_model.sql`.
6. Upserts the data into the normalized operational model.

The staging table is truncated once per pipeline run, before the first city is loaded. All city rows are therefore transformed together after extraction finishes.

The operational model contains:

- `location`
- `weather_condition`
- `current_weather`
- `hourly_forecast`
- `daily_forecast`
- `minutely_forecast`
- `air_pollution`
- `weather_alert`

Natural uniqueness constraints and `ON CONFLICT` clauses make repeated source snapshots safe to process. Locations and weather conditions are updated, while measurements and forecasts are matched by their location and observation or forecast timestamps.

### Stage 2: Operational database to the warehouse

The `operational_to_warehouse` pipeline:

1. Reads operational tables in dependency order.
2. Fully reloads the small reference tables `location` and `weather_condition`.
3. Incrementally extracts fact-like tables using their numeric primary keys.
4. Truncates and reloads the corresponding tables in the warehouse `stg` schema.
5. Runs `data_warehouse/transformations/01_load_weather_dw.sql`.
6. Upserts dimensions and facts and advances the ETL watermarks.
7. Rebuilds the forecast-accuracy fact from matched forecast and actual observations.

Incremental state is stored in `dw.etl_watermark`. For example, the `current_weather` extractor selects only rows whose `current_weather_id` is greater than the saved watermark for `operational.current_weather`. A watermark is advanced only by the warehouse transformation, after rows have reached staging.

### Airflow orchestration


Both DAGs:

- use the `Europe/Warsaw` timezone;
- disable historical catch-up;
- allow only one active run;
- retry failed tasks three times with a one-minute delay;
- print table row counts after a successful pipeline run.

The DAGs are scheduled independently. The warehouse job therefore consumes all operational records available at the moment it starts.

## Warehouse model

The warehouse uses a star-style model in the `dw` schema.

### Dimensions

- `dim_date` — calendar date attributes, including quarter, weekday, and weekend flag.
- `dim_time` — time attributes and part of day.
- `dim_location` — city, country, coordinates, timezone, and UTC offset.
- `dim_weather_condition` — OpenWeather condition code, name, description, and icon.

### Facts

- `fact_current_weather`
- `fact_hourly_forecast`
- `fact_daily_forecast`
- `fact_minutely_forecast`
- `fact_air_pollution`
- `fact_weather_alert`
- `fact_forecast_accuracy`

Facts reference conformed date, time, location, and weather-condition dimensions where applicable. `source_buffer_id` preserves traceability to the operational record and is also used for idempotent warehouse upserts.

`fact_forecast_accuracy` compares hourly forecast temperatures with actual temperatures for the same location and hour. It stores the signed and absolute temperature error and is rebuilt during each warehouse transformation.

## Technology stack

- Python 3.12
- PostgreSQL 16
- Apache Airflow 2.10.5 with `LocalExecutor`
- Docker and Docker Compose
- `uv` for Python dependency management
- Power BI
- pgAdmin 4

## Prerequisites

- Docker with Docker Compose
- An OpenWeather API key with access to One Call API 3.0
- Optional for local Python development: Python 3.12 and `uv`
- Optional for reporting: Power BI Desktop

## Quick start

1. Create the local environment file:

   ```bash
   cp .env.example .env
   ```

2. Set the API key in `.env`:

   ```dotenv
   OPENWEATHER_API_KEY=your_api_key
   ```

3. Start the scheduled platform:

   ```bash
   docker compose up -d operational-db warehouse-db airflow-db airflow-init
   docker compose up -d airflow-webserver airflow-scheduler pgadmin
   ```

4. Check service health:

   ```bash
   docker compose ps
   ```

5. Open the local interfaces:

   - Airflow: <http://localhost:8080>
   - pgAdmin: <http://localhost:5050>

With the example configuration, Airflow credentials are `admin` / `admin`, and pgAdmin credentials are `admin@example.com` / `admin`. Change all default credentials outside a local development environment.

Airflow discovers both DAGs automatically. Enable them in the Airflow UI if they are paused.

## One-shot execution

The `python-app` service runs once and exits. `PIPELINE_MODE` selects the section to execute:

| Value | Behavior |
| --- | --- |
| `api_to_operational` | API to operational database only |
| `operational_to_warehouse` | Operational database to warehouse only |
| `all` | Both stages in sequence |

Run the complete pipeline once:

```bash
docker compose up -d operational-db warehouse-db
docker compose run --rm python-app
```

Run only one stage:

```bash
PIPELINE_MODE=api_to_operational docker compose run --rm python-app
```

The Python container prints row counts for the affected model after processing.

## Configuration

Docker Compose reads `.env` from the project root. The main settings are:

| Variable | Default | Description |
| --- | --- | --- |
| `OPENWEATHER_API_KEY` | empty | Required OpenWeather credential |
| `PIPELINE_MODE` | `all` | Mode used by the one-shot Python service |
| `LOG_LEVEL` | `WARNING` | Python logging level |
| `OPERATIONAL_DB_*` | `postgres` / port `5432` | Operational database settings |
| `WAREHOUSE_DB_*` | `postgres` / port `5433` | Warehouse database settings |
| `AIRFLOW_DB_*` | `airflow` | Airflow metadata database settings |
| `AIRFLOW_PORT` | `8080` | Host port for the Airflow UI |
| `AIRFLOW_USERNAME` | `admin` | Initial Airflow administrator |
| `AIRFLOW_PASSWORD` | `admin` | Initial Airflow password |
| `PGADMIN_PORT` | `5050` | Host port for pgAdmin |

Inside the Docker network, applications use:

- `POSTGRES_DSN` for `operational-db:5432`;
- `WAREHOUSE_POSTGRES_DSN` for `warehouse-db:5432`.

For a non-Docker Python run, define these variables explicitly using host ports:

```bash
export POSTGRES_DSN='postgresql://postgres:postgres@localhost:5432/weather_operational'
export WAREHOUSE_POSTGRES_DSN='postgresql://postgres:postgres@localhost:5433/weather_warehouse'
export OPENWEATHER_API_KEY='your_api_key'
uv run python main.py
```

The API URLs are defined in `scripts/api/api_example.conf`. A local `scripts/api/api.conf` can override that file, but secrets should normally remain in environment variables.

## Database access

When pgAdmin runs in Docker, register the servers with these connection values:

| Database | Host | Port | Database |
| --- | --- | --- | --- |
| Operational | `operational-db` | `5432` | `weather_operational` |
| Warehouse | `warehouse-db` | `5432` | `weather_warehouse` |

From a host database client, use `localhost:5432` for the operational database and `localhost:5433` for the warehouse.

Example validation queries:

```sql
SELECT city_name, observed_at, temp
FROM current_weather
ORDER BY observed_at DESC
LIMIT 20;
```

```sql
SELECT source_name, last_loaded_id, updated_at
FROM dw.etl_watermark
ORDER BY source_name;
```

```sql
SELECT l.city_name, avg(f.abs_temp_error) AS mean_absolute_error
FROM dw.fact_forecast_accuracy AS f
JOIN dw.dim_location AS l USING (location_key)
GROUP BY l.city_name
ORDER BY mean_absolute_error;
```

## Power BI

The report is stored in `power_bi_bd2_project.pbix`. Example dashboard screenshots are available in `powerbi_visualizations/` and cover:

- overall weather metrics;
- current air quality;
- forecasts and forecast accuracy;
- weather alerts;
- a map of monitored Polish locations.

Connect Power BI to the warehouse PostgreSQL instance on `localhost:5433` and import or query tables from the `dw` schema. If Power BI runs on another machine, replace `localhost` with the Docker host address and ensure the warehouse port is reachable.

## Development

Install dependencies:

```bash
uv sync
```

Run the available checks:

```bash
make test
make format-check
make type-check
make lint
```

Apply formatting with:

```bash
make format
```

Tests use Python's `unittest` discovery under `scripts/tests`.

## Project structure

```text
.
├── dags/                         # Airflow DAG definitions
├── data_warehouse/
│   ├── init/                     # Warehouse and staging DDL
│   └── transformations/          # Staging-to-star-schema SQL
├── operational_database/
│   ├── init/                     # Operational model and buffer DDL
│   └── transformations/          # Buffer-to-operational-model SQL
├── powerbi_visualizations/       # Dashboard preview images
├── scripts/
│   ├── api/                      # OpenWeather client and response parser
│   ├── database/                 # Database abstraction and PostgreSQL implementation
│   ├── pipeline/                 # Sources, sinks, load steps, and ELT runner
│   └── tests/                    # Unit and integration-oriented tests
├── sqldeveloper_models/          # SQL Developer Data Modeler artifacts
├── docker-compose.yml            # Local platform definition
├── main.py                       # One-shot pipeline entry point
└── power_bi_bd2_project.pbix     # Power BI report
```

## Operational behavior

### Transactions and failures

Database managers are configured with `autocommit=False`. Pipeline exceptions are wrapped in source- or sink-specific errors, and the database context manager controls commit or rollback behavior. In Airflow, a failed task is retried according to the DAG retry policy.

Because API staging is cleared before extraction, a failure partway through a run prevents the SQL transformation from running but may leave partial rows in the staging buffer. The next run truncates that buffer before loading new data.

Warehouse watermarks are based on increasing operational IDs. Reference dimensions are fully loaded, while measurement and forecast tables are incremental. Do not manually lower operational sequences or reuse primary keys without also reviewing `dw.etl_watermark`.

### Schema initialization

PostgreSQL executes SQL files mounted under `/docker-entrypoint-initdb.d` only when its data volume is first created. The pipeline also executes idempotent setup DDL before staging operations, which protects normal runs when tables already exist.

To apply structural schema changes to an existing environment, use an explicit migration. Removing Docker volumes recreates databases from scratch and permanently deletes local database data.

## Troubleshooting

### The API task returns `401 Unauthorized`

Confirm that `OPENWEATHER_API_KEY` is set, active, and entitled to use One Call API 3.0. Restart the Airflow services after changing `.env` so the containers receive the new value.

### Airflow does not show the DAGs

Check scheduler logs and DAG import errors:

```bash
docker compose logs airflow-scheduler
docker compose exec airflow-scheduler airflow dags list-import-errors
```

### A host port is already in use

Change `OPERATIONAL_DB_PORT`, `WAREHOUSE_DB_PORT`, `AIRFLOW_PORT`, or `PGADMIN_PORT` in `.env`, then recreate the affected service.

### The warehouse contains no new facts

Check, in order:

1. the operational table row counts;
2. the matching `dw.etl_watermark` values;
3. the warehouse `stg` tables;
4. the `operational_to_warehouse` Airflow task logs.

An empty incremental batch is valid when no operational ID is greater than the stored watermark.

### Configuration changes are not visible

Environment variables are captured when containers are created. Recreate the relevant services:

```bash
docker compose up -d --force-recreate airflow-webserver airflow-scheduler
```

## Security notes

- Never commit `.env`, `scripts/api/api.conf`, API keys, or production passwords.
- Replace all example credentials and the Airflow secret key outside local development.
- Restrict exposed PostgreSQL, Airflow, and pgAdmin ports in shared environments.
- Use a dedicated read-only warehouse account for Power BI in production.
