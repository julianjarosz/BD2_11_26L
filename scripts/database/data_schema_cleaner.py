from __future__ import annotations

from logging import Logger
from typing import Protocol, Any, runtime_checkable, final
from schema_metadata_store import SchemaMetadataStore
from dataclasses import dataclass
from step_raport_generator import StepRaportGenerator


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


@runtime_checkable
class DatabaseSchemaCleaner(Protocol):
    """Database schema cleaner interface"""

    schema_store: SchemaMetadataStore
    cleaning_steps: list[CleaningStep]

    raport_generator: StepRaportGenerator | None
    logger: Logger | None

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

    def log_cleaning(
        self, cleaning_step: CleaningStep, *args: tuple, **kwargs: dict[str, Any]
    ) -> None:
        """
        Logs single cleaning_step during cleaning

        Parameters:
            data: Provided data to be logged
            args: Provided arguments by user to provide sufficient logging
            kwargs: Provided keyword arguments by user to provide sufficient logging
        """
        ...

    def clean_data(self, data, *args: tuple, **kwargs: dict[str, Any]):
        """
        Clean provided data based on the schema metadata for the given table.

        Parameters:
            table_name: Name of the table to clean data for.
            data: DatabasePayload containing the data to clean.

        Returns:
            DatabasePayload containing the cleaned data.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        ...
