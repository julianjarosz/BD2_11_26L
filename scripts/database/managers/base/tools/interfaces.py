from __future__ import annotations

from typing import Protocol, runtime_checkable

from scripts.database.managers.base.tools.payload import RejectedDatabaseRow
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import DatabaseRow, DatabaseRows
from scripts.database.stores.schema_metadata_store import TableSchemaMetadata


@runtime_checkable
class PayloadNormalizerInterface(Protocol):
    """Interface for normalizing database payload input."""

    def normalize_rows(self, data: DatabaseRows) -> list[DatabaseRow]:
        """Normalize a row or row collection into a concrete row list."""
        ...

    def normalize_payload(self, data: DatabaseRows | DatabasePayload) -> DatabasePayload:
        """Normalize raw rows or a payload into a validated DatabasePayload."""
        ...


@runtime_checkable
class PayloadSchemaValidatorInterface(Protocol):
    """Interface for validating normalized rows against schema metadata."""

    def validate(
        self, schema: TableSchemaMetadata | None, rows: list[DatabaseRow]
    ) -> tuple[list[DatabaseRow], list[RejectedDatabaseRow]]:
        """Split rows into valid rows and schema-rejected rows."""
        ...
