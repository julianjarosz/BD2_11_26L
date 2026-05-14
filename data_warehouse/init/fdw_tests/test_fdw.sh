#!/bin/bash

docker compose down -v
docker compose up -d

set -a
source .env
set +a

docker compose exec warehouse-db psql -U "$WAREHOUSE_DB_USER" -d "$WAREHOUSE_DB_NAME"
