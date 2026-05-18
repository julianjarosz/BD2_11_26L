from __future__ import annotations

from typing import Mapping, Sequence, Any, final

from enum import StrEnum
from dataclasses import dataclass, field

DatabaseParams = Sequence[Any] | Mapping[str, Any]
DatabaseRow = Mapping[str, Any]
DatabaseRows = DatabaseRow | Sequence[DatabaseRow]


@final
class DatabaseRequestType(StrEnum):
    """
    Supported database request categories.

    Can be added something more idk.
    """

    INSERT_DATA = "insert_data"
    DELETE_DATA = "delete_data"
    UPDATE_DATA = "update_data"


@dataclass(frozen=True, slots=True)
class FailedRow:
    """
    Row that failed to be inserted.

    Parameters:
        table_name: Name of the table that failed to fetch data.
        row: Row that failed to be inserted or fetched.
        message: Message providing additional information about the failure.
        exception: Exception that occurred.
    """

    table_name: str
    row: DatabaseRow
    message: str
    exception: Exception


@dataclass(frozen=True, slots=True)
class DatabaseOperationResult:
    """
    Return type of push_data and fetch_data methods for each database manager.

    Parameters:
        rows: Sequence of rows that were inserted or fetched successfully.
        number_of_rows: Number of rows that were inserted or fetched successfully.
        failed_rows: Sequence of rows that failed to be inserted or fetched.
        number_of_failed_rows: Number of rows that failed to be inserted or fetched.
    """

    successful_rows: Sequence[DatabaseRow]
    failed_rows: Sequence[FailedRow]
    number_of_successful_rows: int = field(init=False)
    number_of_failed_rows: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "number_of_successful_rows", len(self.successful_rows))
        object.__setattr__(self, "number_of_failed_rows", len(self.failed_rows))
