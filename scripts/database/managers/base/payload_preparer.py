from __future__ import annotations

import typing

from scripts.database.managers.base.tools import (
    DatabasePayloadNormalizer,
    PayloadNormalizerInterface,
    PayloadSchemaValidatorInterface,
    PreparedDatabasePayload,
    TableSchemaRowValidator,
)
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import DatabaseRow, DatabaseRows
from scripts.database.stores.schema_metadata_store import SchemaMetadataStore, TableSchemaMetadata


class DatabasePayloadPreparer:
    """Prepare database payloads through normalization and schema validation."""

    def __init__(
        self,
        *,
        schema_metadata_store: SchemaMetadataStore | None = None,
        payload_normalizer: PayloadNormalizerInterface | None = None,
        row_validator: PayloadSchemaValidatorInterface | None = None,
    ) -> None:
        self.schema_metadata_store: SchemaMetadataStore | None = schema_metadata_store
        self.payload_normalizer = payload_normalizer or DatabasePayloadNormalizer()
        self.row_validator = row_validator or TableSchemaRowValidator()

    def fetch_table_metadata(self, table_name: str) -> TableSchemaMetadata | None:
        if self.schema_metadata_store is None:
            return None

        schema: TableSchemaMetadata | None = self.schema_metadata_store.get_table_schema(table_name)
        return schema

    def prepare(
        self, table_name: str, data: DatabaseRows | DatabasePayload
    ) -> PreparedDatabasePayload:
        payload: DatabasePayload = self.payload_normalizer.normalize_payload(data)
        rows: list[DatabaseRow] = typing.cast(list[DatabaseRow], payload.rows)
        schema: TableSchemaMetadata | None = self.fetch_table_metadata(table_name)
        valid_rows, rejected_rows = self.row_validator.validate(schema, rows)
        return PreparedDatabasePayload(
            payload=payload,
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
        )
