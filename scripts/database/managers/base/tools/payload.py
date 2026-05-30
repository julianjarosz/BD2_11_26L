from __future__ import annotations

import dataclasses

from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import DatabaseRow, FailedRow
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
