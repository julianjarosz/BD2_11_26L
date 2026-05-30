from __future__ import annotations

import collections.abc
import dataclasses
from typing import Protocol, runtime_checkable

from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import (
    DatabaseRequestType,
    DatabaseRow,
    DatabaseRows,
    FailedRow,
)
from scripts.database.stores.schema_metadata_store import TableSchemaMetadata
from scripts.errors.database_errors import NormalizingRowsException


@dataclasses.dataclass(frozen=True, slots=True)
class RejectedDatabaseRow:
    row: DatabaseRow
    reason: str

    def to_failed_row(self, table_name: str) -> FailedRow:
        return FailedRow(
            table_name=table_name,
            row=self.row,
            message=f"Rejected by schema validation: {self.reason}",
            exception=NormalizingRowsException(self.reason),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class PreparedDatabasePayload:
    payload: DatabasePayload
    valid_rows: list[DatabaseRow]
    rejected_rows: list[RejectedDatabaseRow]

    @property
    def valid_payload(self) -> DatabasePayload:
        return dataclasses.replace(
            self.payload,
            rows=self.valid_rows,
            number_of_rows=len(self.valid_rows),
        )

    def failed_rows(self, table_name: str) -> list[FailedRow]:
        return [rejected_row.to_failed_row(table_name) for rejected_row in self.rejected_rows]


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


class DatabasePayloadNormalizer:
    """Normalize row collections into the current DatabasePayload shape."""

    @staticmethod
    def normalize_rows(data: DatabaseRows) -> list[DatabaseRow]:
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

    @classmethod
    def normalize_payload(cls, data: DatabaseRows | DatabasePayload) -> DatabasePayload:
        if isinstance(data, DatabasePayload):
            payload = data
            rows = cls.normalize_rows(payload.rows)
        else:
            rows = cls.normalize_rows(data)
            payload = DatabasePayload(
                rows=rows,
                number_of_rows=len(rows),
                request_type=DatabaseRequestType.INSERT_DATA,
            )

        if payload.number_of_rows != len(rows):
            raise NormalizingRowsException(
                "Payload row count mismatch: "
                f"number_of_rows={payload.number_of_rows}, actual_rows={len(rows)}."
            )

        if payload.request_type != DatabaseRequestType.INSERT_DATA:
            raise NormalizingRowsException(
                f"Unsupported database request type: {payload.request_type}."
            )

        return dataclasses.replace(payload, rows=rows, number_of_rows=len(rows))


class TableSchemaRowValidator:
    """Validate rows against cached table schema metadata."""

    def validate(
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
