from __future__ import annotations

import collections.abc
import dataclasses

from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import DatabaseRequestType, DatabaseRow, DatabaseRows
from scripts.errors.database_errors import NormalizingRowsException


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
