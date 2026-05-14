"""Schema metadata storage interfaces for database validation."""

from __future__ import annotations

import abc
import dataclasses
import typing


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


@dataclasses.dataclass(frozen=True, slots=True)
class DatabaseSchemaMetadata:
    """Metadata describing the schema cache for one source database."""

    database_name: str
    tables: tuple[TableSchemaMetadata, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, typing.Any]) -> "DatabaseSchemaMetadata":
        """Create database schema metadata from a plain dictionary."""
        return cls(
            database_name=payload["database_name"],
            tables=tuple(TableSchemaMetadata.from_dict(table) for table in payload["tables"]),
        )

    def to_dict(self) -> dict[str, typing.Any]:
        """Convert database schema metadata to a JSON-serializable dictionary."""
        return {
            "database_name": self.database_name,
            "tables": [table.to_dict() for table in self.tables],
        }

    @property
    def table_names(self) -> set[str]:
        """Return table names available in the metadata cache."""
        return {table.table_name for table in self.tables}


class SchemaMetadataStore(abc.ABC):
    """Interface for storing and reading database schema metadata."""

    @abc.abstractmethod
    def set_table_schema(self, schema: TableSchemaMetadata) -> None:
        """Store schema metadata for one table."""

    def put_table_schema(self, schema: TableSchemaMetadata) -> None:
        """Create or replace schema metadata for one table."""
        self.set_table_schema(schema)

    def update_table_schema(self, schema: TableSchemaMetadata) -> None:
        """Update schema metadata for one table."""
        self.set_table_schema(schema)

    @abc.abstractmethod
    def get_table_schema(self, table_name: str) -> TableSchemaMetadata | None:
        """Fetch schema metadata for one table."""

    @abc.abstractmethod
    def delete_table_schema(self, table_name: str) -> bool:
        """Delete schema metadata for one table."""

    @abc.abstractmethod
    def list_table_schemas(self) -> list[TableSchemaMetadata]:
        """Fetch all table schemas currently stored in metadata storage."""

    def has_table_schema(self, table_name: str) -> bool:
        """Return whether schema metadata exists for one table."""
        return self.get_table_schema(table_name) is not None

    def put_database_schema(self, database_schema: DatabaseSchemaMetadata) -> None:
        """Create or replace schema metadata for every table in one database."""
        for table_schema in database_schema.tables:
            self.put_table_schema(table_schema)

    def update_database_schema(self, database_schema: DatabaseSchemaMetadata) -> None:
        """Update schema metadata for every table in one database."""
        self.put_database_schema(database_schema)

    def get_database_schema(self, database_name: str) -> DatabaseSchemaMetadata:
        """Fetch all cached table metadata as one database metadata object."""
        return DatabaseSchemaMetadata(
            database_name=database_name,
            tables=tuple(self.list_table_schemas()),
        )

    @abc.abstractmethod
    def close(self) -> None:
        """Close metadata storage resources."""
