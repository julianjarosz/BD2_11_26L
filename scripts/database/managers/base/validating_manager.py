from __future__ import annotations

import logging
import typing

from scripts.database.cleaners.data_schema_cleaner import DataSchemaCleaner
from scripts.database.managers.base.database_manager import DatabaseManagerInterface
from scripts.database.managers.base.tools import (
    DatabasePayloadNormalizer,
    PayloadNormalizerInterface,
    PayloadSchemaValidatorInterface,
    PreparedDatabasePayload,
    RejectedDatabaseRow,
    TableSchemaRowValidator,
)
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import (
    DatabaseRow,
    DatabaseRows,
)
from scripts.database.stores.schema_metadata_store import SchemaMetadataStore, TableSchemaMetadata


class ValidatingDatabaseManager(DatabaseManagerInterface):
    """Base database manager with payload normalization and schema validation."""

    def __init__(
        self,
        *,
        schema_metadata_store: SchemaMetadataStore | None = None,
        data_schema_cleaner: DataSchemaCleaner | None = None,
        payload_normalizer: PayloadNormalizerInterface | None = None,
        row_validator: PayloadSchemaValidatorInterface | None = None,
        logger: logging.Logger | None = None,
        default_logger: logging.Logger | None = None,
    ) -> None:
        self.schema_metadata_store: SchemaMetadataStore | None = schema_metadata_store
        self.data_schema_cleaner: DataSchemaCleaner | None = data_schema_cleaner
        self.payload_normalizer = payload_normalizer or DatabasePayloadNormalizer()
        self.row_validator = row_validator or TableSchemaRowValidator()
        self.logger = logger or default_logger or logging.getLogger(self.__class__.__module__)

    def fetch_table_metadata(self, table_name: str) -> TableSchemaMetadata | None:
        if self.schema_metadata_store is None:
            self.logger.warning(
                "Schema metadata store is not configured. Skipping row validation for table %s.",
                table_name,
            )
            return None

        schema: TableSchemaMetadata | None = self.schema_metadata_store.get_table_schema(table_name)
        if schema is None:
            self.logger.warning(
                "Schema metadata for table %s was not found. Skipping row validation.",
                table_name,
            )
        return schema

    @staticmethod
    def _normalize_rows(data: DatabaseRows) -> list[DatabaseRow]:
        return DatabasePayloadNormalizer.normalize_rows(data)

    def _filter_invalid_rows(
        self, schema: TableSchemaMetadata | None, rows: list[DatabaseRow]
    ) -> tuple[list[DatabaseRow], list[RejectedDatabaseRow]]:
        return self.row_validator.validate(schema, rows)

    def _prepare_payload_for_operation(
        self, table_name: str, data: DatabaseRows | DatabasePayload
    ) -> PreparedDatabasePayload:
        payload: DatabasePayload = self.payload_normalizer.normalize_payload(data)
        rows: list[DatabaseRow] = typing.cast(list[DatabaseRow], payload.rows)
        schema: TableSchemaMetadata | None = self.fetch_table_metadata(table_name)
        valid_rows, rejected_rows = self._filter_invalid_rows(schema, rows)
        return PreparedDatabasePayload(
            payload=payload,
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
        )

    def _log_payload_received(self, table_name: str, payload: DatabasePayload) -> None:
        self.logger.info(
            "Processing database payload: request_type=%s table=%s rows=%s created_at=%s",
            payload.request_type,
            table_name,
            payload.number_of_rows,
            payload.created_at.isoformat(),
        )

    def _log_rejected_rows(self, table_name: str, rejected_rows: list[RejectedDatabaseRow]) -> None:
        for rejected_row in rejected_rows:
            self.logger.warning(
                "Rejected row for table %s: %s. Row: %s",
                table_name,
                rejected_row.reason,
                rejected_row.row,
            )

    def _log_no_valid_rows(
        self, table_name: str, prepared_payload: PreparedDatabasePayload
    ) -> None:
        self.logger.warning(
            "No valid rows to process for table %s: submitted=%s rejected=%s",
            table_name,
            prepared_payload.payload.number_of_rows,
            len(prepared_payload.rejected_rows),
        )

    @classmethod
    def _normalize_payload(cls, data: DatabaseRows | DatabasePayload) -> DatabasePayload:
        return DatabasePayloadNormalizer.normalize_payload(data)

    def __enter__(self) -> "ValidatingDatabaseManager":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: typing.Any,
    ) -> None:
        self.close()

    def close(self) -> None:
        raise NotImplementedError


DatabaseManagerWithSchemaValidation = ValidatingDatabaseManager
