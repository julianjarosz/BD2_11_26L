from __future__ import annotations

from typing import Protocol, Any, runtime_checkable, final
from scripts.database.stores.schema_metadata_store import SchemaMetadataStore
from dataclasses import dataclass
from scripts.database.models.step_raport_generator import StepRaportGenerator
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import FailedRow


@dataclass(frozen=True, slots=True)
class CleaningStep:
    """
    Metadata about cleaning step performed during cleaning

    Paramters:
        data_before: Data before cleaning
        data_after: Data after cleaning
        message: Additional message to log during cleaning
        exception: If error occured, save this error in exception placeholder and log
    """

    data_before: Any
    data_after: Any
    message: str | None
    exception: Exception | None


@dataclass(frozen=True, slots=True)
class CleaningResults:
    # TODO - add docs for this dataclass
    cleaned_payload: DatabasePayload
    failed_rows: list[FailedRow]


@runtime_checkable
class DataSchemaCleaner(Protocol):
    """Database schema cleaner interface"""

    schema_store: SchemaMetadataStore
    cleaning_steps: list[CleaningStep]

    raport_generator: StepRaportGenerator | None

    @final
    def clean_buffer(self) -> None:
        """Can be performed before each cleaning and maybe even should be..."""
        ...

    @final
    def cleaning_raport(self, *args: tuple, **kwargs: dict[str, Any]) -> None:
        """
        Generates cleaning raport in file format based od cleaning_steps

        Parameters:
            args: Provided arguments by user to provide sufficient raport generating
            kwargs: Provided keyword arguments by user to provide sufficient raport generating
        """
        ...

    def clean_data(
        self,
        data: DatabasePayload,
        *args: tuple,
        **kwargs: dict[str, Any],
    ) -> CleaningResults:
        """
        Clean provided data based on the schema metadata for the given table.

        Parameters:
            table_name: Name of the table to clean data for.
            data: DatabasePayload containing the data to clean.

        Returns:
            CleaningResults containing the cleaned payload and rows that failed cleaning.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        ...
