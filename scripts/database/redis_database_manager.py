"""Redis implementation of the database manager interface for caching and temporary storage."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import typing

import redis

from scripts.database.base_database_manager import (
    BaseDatabaseManager,
    PreparedDatabasePayload,
)
from scripts.database.database_manager import (
    DatabasePayload,
    DatabaseRow,
    DatabaseRows,
)
from scripts.database.schema_metadata_store import (
    SchemaMetadataStore,
)

REDIS_URL_ENV_VAR = "REDIS_URL"
DEFAULT_REDIS_KEY_PREFIX = "database:data"
LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class RedisDatabaseManagerContext:
    schema_metadata_store: SchemaMetadataStore | None
    logger: logging.Logger
    key_prefix: str = DEFAULT_REDIS_KEY_PREFIX

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "schema_metadata_store": self.schema_metadata_store,
            "logger": self.logger,
            "key_prefix": self.key_prefix,
        }


class RedisDatabaseManager(BaseDatabaseManager):
    """Database manager backed by a Redis connection for caching and temporary storage."""

    def __init__(
        self,
        url: str | None = None,
        *,
        schema_metadata_store: SchemaMetadataStore | None = None,
        logger: logging.Logger | None = None,
        key_prefix: str = DEFAULT_REDIS_KEY_PREFIX,
        **connection_kwargs: typing.Any,
    ) -> None:
        """Create a Redis manager.

        Args:
            url: Redis connection URL. If omitted, connection keyword arguments
                such as ``host``, ``port``, ``db``, etc. can be supplied.
            schema_metadata_store: Optional metadata store for table schema caching.
            logger: Optional logger for rejected row messages.
            key_prefix: Prefix for Redis keys storing data. Defaults to ``database:data``.
            connection_kwargs: Additional arguments forwarded to redis.Redis.
        """
        super().__init__(
            schema_metadata_store=schema_metadata_store,
            logger=logger,
            default_logger=LOGGER,
        )
        self.key_prefix: str = key_prefix

        if url:
            self.connection: redis.Redis = redis.from_url(url, **connection_kwargs)
        else:
            self.connection = redis.Redis(**connection_kwargs)

    @classmethod
    def create_from_env(
        cls, context: RedisDatabaseManagerContext, env_var: str = REDIS_URL_ENV_VAR
    ) -> "RedisDatabaseManager":
        """Create a manager using a Redis URL stored in an environment variable.

        By default this method reads ``REDIS_URL``. The value must be a valid
        Redis connection URL, for example::

            redis://localhost:6379/0

        This is the preferred constructor for Docker Compose and cloud
        deployments because the application can receive connection details from
        environment variables instead of hardcoding credentials in source code.

        Args:
            context: Configuration context for the Redis manager.
            env_var: Name of the environment variable containing the Redis URL.
                Defaults to ``REDIS_URL``.

        Raises:
            ValueError: If the environment variable is missing or empty.

        Returns:
            A configured ``RedisDatabaseManager`` instance.
        """
        url: str = os.getenv(env_var, "").strip()
        if not url:
            raise ValueError(f"Redis URL not found in environment variable {env_var}.")
        return cls(url, **context.to_dict())

    def _store_valid_rows(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> int:
        """Store all valid rows from a prepared payload.

        This method stores each valid row as a JSON value in Redis using a key
        constructed from the table name and a timestamp-based identifier. Each
        row is stored independently, allowing for flexible retrieval and cleanup.

        If storage fails, the exception is logged with payload context and then
        re-raised so callers can decide how to handle the failure.
        """
        try:
            rows_stored = 0
            for idx, row in enumerate(prepared_payload.valid_rows):
                row_key = f"{self.key_prefix}:{table_name}:{prepared_payload.payload.created_at.timestamp()}:{idx}"
                self.connection.set(row_key, json.dumps(row, default=str))
                rows_stored += 1
        except Exception:
            self._log_payload_store_failed(table_name, prepared_payload)
            raise

        return rows_stored

    def push_data(self, table_name: str, data: DatabaseRows | DatabasePayload) -> int:
        """Validate and store one or more rows in Redis.

        ``data`` can be either a single mapping or a sequence of mappings. Each
        mapping represents one record, where keys are field names and values
        are the values to store, for example::

            {
                "city": "Warsaw",
                "temperature": 18.5,
                "measured_at": "2024-01-01T10:00:00Z",
            }

        Before storing in Redis, rows are normalized into a list and validated
        against table metadata. Invalid rows are not stored and are logged with
        the reason for rejection. Valid rows are stored independently with
        keys constructed from the table name and timestamp.

        Args:
            table_name: Logical table name for organizing stored data.
            data: A row mapping or a sequence of row mappings to store.

        Raises:
            ValueError: If no rows are provided or a row has no columns.
            TypeError: If ``data`` contains values that are not mappings.
            redis.RedisError: If Redis rejects the storage operation.

        Returns:
            Number of rows accepted for storage.
        """
        prepared_payload: PreparedDatabasePayload = self._prepare_payload_for_operation(table_name, data)
        self._log_payload_received(table_name, prepared_payload.payload)
        self._log_rejected_rows(table_name, prepared_payload.rejected_rows)

        if not prepared_payload.valid_rows:
            self._log_no_valid_rows(table_name, prepared_payload)
            return 0

        stored_rows: int = self._store_valid_rows(table_name, prepared_payload)
        self._log_payload_stored(table_name, prepared_payload)
        return stored_rows

    def fetch_data(self, pattern: str, scan_count: int = 100) -> list[DatabaseRow]:
        """Retrieve rows from Redis matching a key pattern.

        This method uses Redis SCAN to efficiently retrieve data matching a
        pattern without blocking the Redis server. Each matched key is fetched
        and decoded as JSON into a dictionary.

        Args:
            pattern: Redis key pattern to match, for example ``database:data:weather_observations:*``.
            scan_count: Number of keys to retrieve per scan iteration.

        Returns:
            A list of row mappings. If no keys match the pattern, the list is empty.
        """
        rows: list[DatabaseRow] = []
        cursor = 0

        while True:
            cursor, keys = self.connection.scan(cursor, match=pattern, count=scan_count)
            for key in keys:
                value = self.connection.get(key)
                if value:
                    try:
                        row = json.loads(value)
                        rows.append(row)
                    except json.JSONDecodeError as e:
                        self.logger.warning("Failed to decode JSON for key %s: %s", key, e)

            if cursor == 0:
                break

        return rows

    def clear_table_data(self, table_name: str) -> int:
        """Remove all stored rows for a given table from Redis.

        Args:
            table_name: The table name whose data should be cleared.

        Returns:
            Number of keys removed.
        """
        pattern = f"{self.key_prefix}:{table_name}:*"
        cursor = 0
        deleted = 0

        while True:
            cursor, keys = self.connection.scan(cursor, match=pattern, count=100)
            if keys:
                deleted += self.connection.delete(*keys)
            if cursor == 0:
                break

        self.logger.info("Cleared %d rows for table %s from Redis", deleted, table_name)
        return deleted

    def close(self) -> None:
        """Close the Redis connection."""
        self.connection.close()

    def _log_payload_store_failed(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> None:
        self.logger.exception(
            "Failed to store database payload: sender=%s table=%s valid_rows=%s rejected_rows=%s",
            prepared_payload.payload.sender,
            table_name,
            len(prepared_payload.valid_rows),
            len(prepared_payload.rejected_rows),
        )

    def _log_payload_stored(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> None:
        self.logger.info(
            "Stored database payload: sender=%s table=%s stored=%s rejected=%s",
            prepared_payload.payload.sender,
            table_name,
            len(prepared_payload.valid_rows),
            len(prepared_payload.rejected_rows),
        )


ReddisDatabaseManager = RedisDatabaseManager
