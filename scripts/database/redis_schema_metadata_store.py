"""Redis implementation of schema metadata storage."""

from __future__ import annotations

import json
import os

from scripts.database.redis_database_manager import RedisDatabaseManager
from scripts.database.schema_metadata_store import (
    SchemaMetadataStore,
    TableSchemaMetadata,
)
from scripts.utils import fetch_config_value

REDIS_URL_ENV_VAR: str = fetch_config_value("consts.conf", "redis.url_env_var")
DEFAULT_SCHEMA_KEY_PREFIX: str = fetch_config_value(
    "consts.conf", "redis.default_schema_key_prefix"
)
DEFAULT_REDIS_SCAN_COUNT: int = int(fetch_config_value("consts.conf", "redis.scan_count"))


class RedisSchemaMetadataStore(SchemaMetadataStore):
    """Redis-backed metadata storage for source database schemas."""

    def __init__(
        self,
        redis_database_manager: RedisDatabaseManager,
        *,
        key_prefix: str = DEFAULT_SCHEMA_KEY_PREFIX,
    ) -> None:
        self.redis_database_manager = redis_database_manager
        self.key_prefix = key_prefix

    @classmethod
    def from_url(
        cls, redis_url: str, *, key_prefix: str = DEFAULT_SCHEMA_KEY_PREFIX
    ) -> "RedisSchemaMetadataStore":
        """Create Redis metadata storage from a Redis connection URL."""
        return cls(RedisDatabaseManager(redis_url), key_prefix=key_prefix)

    @classmethod
    def from_env(
        cls, env_var: str = REDIS_URL_ENV_VAR, *, key_prefix: str = DEFAULT_SCHEMA_KEY_PREFIX
    ) -> "RedisSchemaMetadataStore":
        """Create Redis metadata storage from an environment variable."""
        return cls.from_url(cls._load_redis_url(env_var), key_prefix=key_prefix)

    def set_table_schema(self, schema: TableSchemaMetadata) -> None:
        """Store schema metadata as JSON under a stable Redis key."""
        self.redis_database_manager.connection.set(
            self._schema_key(schema.table_name), json.dumps(schema.to_dict())
        )

    def get_table_schema(self, table_name: str) -> TableSchemaMetadata | None:
        """Fetch and deserialize schema metadata from Redis."""
        payload = self.redis_database_manager.connection.get(self._schema_key(table_name))
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return TableSchemaMetadata.from_dict(json.loads(payload))

    def delete_table_schema(self, table_name: str) -> bool:
        """Delete schema metadata for one table from Redis."""
        return bool(self.redis_database_manager.connection.delete(self._schema_key(table_name)))

    def list_table_names(self, scan_count: int = DEFAULT_REDIS_SCAN_COUNT) -> list[str]:
        """List table names with schema metadata stored in Redis."""
        table_names: list[str] = []
        cursor = 0
        while True:
            cursor, keys = self.redis_database_manager.connection.scan(
                cursor,
                match=f"{self.key_prefix}:*",
                count=scan_count,
            )
            table_names.extend(self._table_name_from_schema_key(key) for key in keys)
            if cursor == 0:
                break
        return sorted(table_names)

    def list_table_schemas(self) -> list[TableSchemaMetadata]:
        """Fetch all table schemas currently stored in Redis."""
        table_schemas: list[TableSchemaMetadata] = []
        for table_name in self.list_table_names():
            table_schema = self.get_table_schema(table_name)
            if table_schema is not None:
                table_schemas.append(table_schema)
        return table_schemas

    def clear_table_schemas(self, scan_count: int = DEFAULT_REDIS_SCAN_COUNT) -> int:
        """Delete all table schema metadata entries from Redis."""
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = self.redis_database_manager.connection.scan(
                cursor,
                match=f"{self.key_prefix}:*",
                count=scan_count,
            )
            if keys:
                deleted += self.redis_database_manager.connection.delete(*keys)
            if cursor == 0:
                break
        return deleted

    def close(self) -> None:
        """Close the Redis connection pool."""
        self.redis_database_manager.close()

    def _schema_key(self, table_name: str) -> str:
        return f"{self.key_prefix}:{table_name}"

    def _table_name_from_schema_key(self, schema_key: str | bytes) -> str:
        if isinstance(schema_key, bytes):
            schema_key = schema_key.decode("utf-8")
        return schema_key.removeprefix(f"{self.key_prefix}:")

    @staticmethod
    def _load_redis_url(env_var: str = REDIS_URL_ENV_VAR) -> str:
        redis_url = os.getenv(env_var, "").strip()
        if not redis_url:
            raise ValueError(f"Redis URL not found in environment variable {env_var}.")
        return redis_url
