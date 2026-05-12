"""Backward-compatible exports for database manager classes."""

from scripts.database.database_manager import DatabaseManager, DatabasePayload, DatabaseRequestType
from scripts.database.postgresql_database_manager import PostgreSQLDatabaseManager
from scripts.database.redis_database_manager import RedisDatabaseManager, ReddisDatabaseManager
from scripts.database.redis_schema_metadata_store import RedisSchemaMetadataStore
from scripts.database.schema_metadata_store import (
    DatabaseSchemaMetadata,
    SchemaMetadataStore,
    TableSchemaMetadata,
)

__all__ = [
    "DatabaseManager",
    "DatabasePayload",
    "DatabaseRequestType",
    "DatabaseSchemaMetadata",
    "PostgreSQLDatabaseManager",
    "RedisDatabaseManager",
    "RedisSchemaMetadataStore",
    "ReddisDatabaseManager",
    "SchemaMetadataStore",
    "TableSchemaMetadata",
]
