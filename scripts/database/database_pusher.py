"""Backward-compatible exports for database manager classes."""

from scripts.database.database_manager import DatabaseManager
from scripts.database.postgresql_database_manager import PostgreSQLDatabaseManager
from scripts.database.schema_metadata_store import (
    RedisSchemaMetadataStore,
    SchemaMetadataStore,
    TableSchemaMetadata,
)

__all__ = [
    "DatabaseManager",
    "PostgreSQLDatabaseManager",
    "RedisSchemaMetadataStore",
    "SchemaMetadataStore",
    "TableSchemaMetadata",
]
