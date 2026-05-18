from __future__ import annotations

import collections.abc
import dataclasses
import logging
import typing

from scripts.database.managers.database_manager import (
    DatabaseManagerInterface,
)
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import DatabaseRequestType, DatabaseRow, DatabaseRows
from scripts.database.stores.schema_metadata_store import SchemaMetadataStore, TableSchemaMetadata
from scripts.database.cleaners.data_schema_cleaner import DataSchemaCleaner
from scripts.errors.database_errors import NormalizingRowsException


@dataclasses.dataclass(frozen=True, slots=True)
class RejectedDatabaseRow:
    row: DatabaseRow
    reason: str


@dataclasses.dataclass(frozen=True, slots=True)
class PreparedDatabasePayload:
    payload: DatabasePayload
    valid_rows: list[DatabaseRow]
    rejected_rows: list[RejectedDatabaseRow]


class DatabaseManagerWithSchemaValidation(DatabaseManagerInterface):
    """
    Database manager with schema validation.

    This class provides a base implementation for a database manager with schema validation.
    It is used to validate the schema of the data before inserting it into the database.
    """

    def __init__(
        self,
        *,
        schema_metadata_store: SchemaMetadataStore | None = None,
        data_schema_cleaner: DataSchemaCleaner | None = None,
        logger: logging.Logger | None = None,
        default_logger: logging.Logger | None = None,
    ) -> None:
        self.schema_metadata_store: SchemaMetadataStore | None = schema_metadata_store
        self.data_schema_cleaner: DataSchemaCleaner | None = data_schema_cleaner
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
        if isinstance(data, collections.abc.Mapping):
            rows = [data]
        else:
            rows = list(data)

        if not rows:
            raise NormalizingRowsException("At least one row is required to push data.")

        if not all(isinstance(row, collections.abc.Mapping) for row in rows):
            raise TypeError("Rows must be mappings of column names to values.")

        if any(not row for row in rows):
            raise NormalizingRowsException("Rows must contain at least one column.")

        return rows

    def _filter_invalid_rows(
        self, schema: TableSchemaMetadata | None, rows: list[DatabaseRow]
    ) -> tuple[list[DatabaseRow], list[RejectedDatabaseRow]]:
        if schema is None:
            return rows, []

        valid_rows: list[DatabaseRow] = []
        rejected_rows: list[RejectedDatabaseRow] = []
        known_columns: set[str] = schema.column_names
        required_columns: set[str] = schema.required_column_names

        for row in rows:
            row_columns: set[str] = set(row.keys())
            unknown_columns: set[str] = row_columns - known_columns
            missing_required_columns: set[str] = required_columns - row_columns

            if unknown_columns:
                rejected_rows.append(
                    RejectedDatabaseRow(
                        row=row,
                        reason=f"unknown columns: {', '.join(sorted(unknown_columns))}",
                    )
                )
                continue

            if missing_required_columns:
                rejected_rows.append(
                    RejectedDatabaseRow(
                        row=row,
                        reason=(
                            "missing required columns: "
                            f"{', '.join(sorted(missing_required_columns))}"
                        ),
                    )
                )
                continue

            valid_rows.append(row)

        return valid_rows, rejected_rows

    def _prepare_payload_for_operation(
        self, table_name: str, data: DatabaseRows | DatabasePayload
    ) -> PreparedDatabasePayload:
        payload: DatabasePayload = self._normalize_payload(data)
        rows: list[DatabaseRow] = typing.cast(list[DatabaseRow], payload.data)
        schema: TableSchemaMetadata | None = self.fetch_table_metadata(table_name)
        valid_rows, rejected_rows = self._filter_invalid_rows(schema, rows)
        return PreparedDatabasePayload(
            payload=payload,
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
        )

    def _log_payload_received(self, table_name: str, payload: DatabasePayload) -> None:
        self.logger.info(
            "Processing database payload: request_type=%s sender=%s table=%s rows=%s created_at=%s",
            payload.request_type,
            payload.sender,
            table_name,
            payload.n_rows,
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
            "No valid rows to process for table %s: sender=%s submitted=%s rejected=%s",
            table_name,
            prepared_payload.payload.sender,
            prepared_payload.payload.n_rows,
            len(prepared_payload.rejected_rows),
        )

    @classmethod
    def _normalize_payload(cls, data: DatabaseRows | DatabasePayload) -> DatabasePayload:
        payload: DatabasePayload = (
            data if isinstance(data, DatabasePayload) else DatabasePayload(data=data)
        )
        rows: list[DatabaseRows] = cls._normalize_rows(payload.data)
        n_rows: int = len(rows)

        if payload.n_rows is not None and payload.n_rows != n_rows:
            raise NormalizingRowsException(
                f"Payload row count mismatch: n_rows={payload.n_rows}, actual_rows={n_rows}."
            )
        if payload.request_type != DatabaseRequestType.PUSH_DATA:
            raise NormalizingRowsException(
                f"Unsupported database request type: {payload.request_type}."
            )

        return dataclasses.replace(payload, data=rows, n_rows=n_rows)

    def __enter__(self) -> "BaseDatabaseManager":
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
