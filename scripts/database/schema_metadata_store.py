"""Schema metadata storage interfaces for database validation."""

from __future__ import annotations

import abc
import dataclasses
import json
import os
import typing

import redis

REDIS_URL_ENV_VAR = "REDIS_URL"
DEFAULT_SCHEMA_KEY_PREFIX = "database:schema"


@dataclasses.dataclass(frozen=True, slots=True)
class ColumnMetadata:
    """Metadata describing one database table column."""

    name: str
    data_type: str | None = None
    is_nullable: bool = True
    has_default: bool = False
    is_identity: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, typing.Any]) -> "ColumnMetadata":
        """Create column metadata from a plain dictionary."""
        return cls(
            name=payload["name"],
            data_type=payload.get("data_type"),
            is_nullable=payload.get("is_nullable", True),
            has_default=payload.get("has_default", False),
            is_identity=payload.get("is_identity", False),
        )

    def to_dict(self) -> dict[str, typing.Any]:
        """Convert column metadata to a JSON-serializable dictionary."""
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, slots=True)
class TableSchemaMetadata:
    """Metadata describing columns available in one database table."""

    table_name: str
    columns: tuple[ColumnMetadata, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, typing.Any]) -> "TableSchemaMetadata":
        """Create table schema metadata from a plain dictionary."""
        return cls(
            table_name=payload["table_name"],
            columns=tuple(ColumnMetadata.from_dict(column) for column in payload["columns"]),
        )

    def to_dict(self) -> dict[str, typing.Any]:
        """Convert table schema metadata to a JSON-serializable dictionary."""
        return {
            "table_name": self.table_name,
            "columns": [column.to_dict() for column in self.columns],
        }

    @property
    def column_names(self) -> set[str]:
        """Return all column names known for the table."""
        return {column.name for column in self.columns}

    @property
    def required_column_names(self) -> set[str]:
        """Return columns that must be present in incoming rows."""
        return {
            column.name
            for column in self.columns
            if not column.is_nullable and not column.has_default and not column.is_identity
        }


class SchemaMetadataStore(abc.ABC):
    """Interface for storing and reading database schema metadata."""

    @abc.abstractmethod
    def set_table_schema(self, schema: TableSchemaMetadata) -> None:
        """Store schema metadata for one table."""

    @abc.abstractmethod
    def get_table_schema(self, table_name: str) -> TableSchemaMetadata | None:
        """Fetch schema metadata for one table."""

    @abc.abstractmethod
    def close(self) -> None:
        """Close metadata storage resources."""


class RedisSchemaMetadataStore(SchemaMetadataStore):
    """Redis-backed schema metadata storage."""

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        *,
        redis_url: str | None = None,
        key_prefix: str = DEFAULT_SCHEMA_KEY_PREFIX,
    ) -> None:
        self.redis = redis_client or redis.Redis.from_url(redis_url or self._load_redis_url(), decode_responses=True)
        self.key_prefix = key_prefix

    @classmethod
    def from_env(cls, env_var: str = REDIS_URL_ENV_VAR) -> "RedisSchemaMetadataStore":
        """Create Redis metadata storage from an environment variable."""
        return cls(redis_url=cls._load_redis_url(env_var))

    def set_table_schema(self, schema: TableSchemaMetadata) -> None:
        """Store schema metadata as JSON under a stable Redis key."""
        self.redis.set(self._schema_key(schema.table_name), json.dumps(schema.to_dict()))

    def get_table_schema(self, table_name: str) -> TableSchemaMetadata | None:
        """Fetch and deserialize schema metadata from Redis."""
        payload = self.redis.get(self._schema_key(table_name))
        if payload is None:
            return None
        return TableSchemaMetadata.from_dict(json.loads(payload))

    def close(self) -> None:
        """Close the Redis connection pool."""
        self.redis.close()

    def _schema_key(self, table_name: str) -> str:
        return f"{self.key_prefix}:{table_name}"

    @staticmethod
    def _load_redis_url(env_var: str = REDIS_URL_ENV_VAR) -> str:
        redis_url = os.getenv(env_var, "").strip()
        if not redis_url:
            raise ValueError(f"Redis URL not found in environment variable {env_var}.")
        return redis_url
