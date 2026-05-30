from __future__ import annotations

from scripts.database.managers.base.tools.payload import RejectedDatabaseRow
from scripts.database.models.database_types import DatabaseRow
from scripts.database.stores.schema_metadata_store import TableSchemaMetadata


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
