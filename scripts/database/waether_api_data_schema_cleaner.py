from __future__ import annotations


from copy import deepcopy
from typing import final, Any
from logging import Logger
from schema_metadata_store import SchemaMetadataStore, TableSchemaMetadata
from step_raport_generator import StepRaportGenerator
from data_schema_cleaner import CleaningResults, CleaningStep
from database_payload import DatabasePayload
from database_types import DatabaseRow, FailedRow


class ToPostgreSQLDataSchemaCleaner:
    """Cleaner for data incoming from source to PostgreSQL database."""

    def __init__(
        self,
        schema_store: SchemaMetadataStore,
        logger: Logger | None = None,
        raport_generator: StepRaportGenerator | None = None,
    ) -> None:
        self.schema_store: SchemaMetadataStore = schema_store
        self.cleaning_steps: list[CleaningStep] = []
        self.logger: Logger | None = logger
        self.raport_generator: StepRaportGenerator | None = raport_generator

    @final
    def clean_buffer(self) -> None:
        self.cleaning_steps.clear()

    def _clean_row(self, row: DatabaseRow, table_metadata: TableSchemaMetadata) -> DatabaseRow:
        # TODO - add documentation for this method
        # TODO - think more about possible cleaning solution for rows with invalid data
        cleared_row: DatabaseRow = deepcopy(row)
        for column_name, column_value in row.items():
            if column_name not in table_metadata.column_names:
                # TODO - log warning that column is not in table metadata
                _ = cleared_row.pop(column_name)
                continue

            if column_name in table_metadata.required_column_names and column_value is None:
                # TODO - log warning that required column is not provided and column in database is not nullable
                _ = cleared_row.pop(column_name)
                continue

        return cleared_row

    def clean_data(
        self, data: DatabasePayload, *args: tuple, **kwargs: dict[str, Any]
    ) -> CleaningResults:
        # TODO - add documentation for this method
        table_name: str | None = kwargs.get("table_name", None)
        if table_name is None:
            raise ValueError("table_name keyword is not specified!")

        table_schema: TableSchemaMetadata | None = self.schema_store.get_table_schema(table_name)
        if table_schema is None:
            raise ValueError(f"Cannot provided table in schema with provided name: {table_name}")
        self.clean_buffer()
        cleaned_rows: list[DatabaseRow] = []
        failed_rows: list[FailedRow] = []

        for row in data.rows:
            try:
                cleaned_row: DatabaseRow = self._clean_row(row, table_schema)
                cleaned_rows.append(cleaned_row)
                self.cleaning_steps.append(
                    CleaningStep(
                        data_before=row,
                        data_after=cleaned_row,
                        message="Row cleaned properly",
                        exception=None,
                    )
                )
            except Exception as exep:
                failed_rows.append(
                    FailedRow(
                        table_name=table_name,
                        row=row,
                        message=f"Invalid row cleaning - {str(exep)}",
                        exception=exep,
                    )
                )
                self.cleaning_steps.append(
                    CleaningStep(
                        data_before=row,
                        data_after=row,
                        message=f"Invalid row cleaning - {str(exep)}",
                        exception=exep,
                    )
                )

        return CleaningResults(
            cleaned_payload=DatabasePayload(
                rows=cleaned_rows,
                number_of_rows=len(cleaned_rows),
                created_at=data.created_at,
                request_type=data.request_type,
            ),
            failed_rows=failed_rows,
        )
