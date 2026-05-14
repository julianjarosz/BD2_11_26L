#!/bin/sh
set -eu

# Etap 2: polaczenie hurtowni z baza operacyjna przez postgres_fdw.
# Ten plik jest .sh, bo zwykle pliki .sql w docker-entrypoint-initdb.d
# nie podstawiaja zmiennych z docker-compose/.env.

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${OPERATIONAL_DB_HOST:?OPERATIONAL_DB_HOST is required}"
: "${OPERATIONAL_DB_PORT:?OPERATIONAL_DB_PORT is required}"
: "${OPERATIONAL_DB_USER:?OPERATIONAL_DB_USER is required}"
: "${OPERATIONAL_DB_PASSWORD:?OPERATIONAL_DB_PASSWORD is required}"
: "${OPERATIONAL_DB_NAME:?OPERATIONAL_DB_NAME is required}"

echo "Waiting for operational database before creating FDW connection..."
until PGPASSWORD="${OPERATIONAL_DB_PASSWORD}" psql \
    --host="${OPERATIONAL_DB_HOST}" \
    --port="${OPERATIONAL_DB_PORT}" \
    --username="${OPERATIONAL_DB_USER}" \
    --dbname="${OPERATIONAL_DB_NAME}" \
    --command="SELECT 1" >/dev/null 2>&1; do
    sleep 1
done

psql \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --set=operational_host="${OPERATIONAL_DB_HOST}" \
    --set=operational_port="${OPERATIONAL_DB_PORT}" \
    --set=operational_db="${OPERATIONAL_DB_NAME}" \
    --set=operational_user="${OPERATIONAL_DB_USER}" \
    --set=operational_password="${OPERATIONAL_DB_PASSWORD}" <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
CREATE SCHEMA IF NOT EXISTS src;

CREATE SERVER IF NOT EXISTS operational_server
FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (
    host :'operational_host',
    port :'operational_port',
    dbname :'operational_db'
);

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
SERVER operational_server
OPTIONS (
    user :'operational_user',
    password :'operational_password'
);

IMPORT FOREIGN SCHEMA public
LIMIT TO (
    location,
    weather_condition,
    current_weather,
    hourly_forecast,
    daily_forecast,
    minutely_forecast,
    air_pollution,
    weather_alert
)
FROM SERVER operational_server
INTO src;
SQL
