"""Database manager interface used by concrete database backends."""

from __future__ import annotations

import abc
import dataclasses
import datetime
import enum
import typing

from scripts.utils import fetch_config_value

DatabaseParams = typing.Sequence[typing.Any] | typing.Mapping[str, typing.Any]
DatabaseRow = typing.Mapping[str, typing.Any]
DatabaseRows = DatabaseRow | typing.Sequence[DatabaseRow]
DEFAULT_DATABASE_PAYLOAD_SENDER: str = fetch_config_value(
    "consts.conf", "database_payload.default_sender"
)


class DatabaseRequestType(enum.StrEnum):
    """Supported database request categories."""

    PUSH_DATA = "push_data"


@dataclasses.dataclass(frozen=True, slots=True)
class DatabasePayload:
    """Envelope for database writes with metadata useful for logging."""

    data: DatabaseRows
    n_rows: int | None = None
    created_at: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    request_type: DatabaseRequestType = DatabaseRequestType.PUSH_DATA
    sender: str = DEFAULT_DATABASE_PAYLOAD_SENDER


class DatabaseManager(abc.ABC):
    """Interface for pushing data to and fetching data from a database."""

    @abc.abstractmethod
    def push_data(self, table_name: str, data: DatabaseRows | DatabasePayload) -> int:
        """Push one or more rows into ``table_name``.

        Returns the number of rows submitted to the database.
        """
        pass

    @abc.abstractmethod
    def fetch_data(self, query: str, params: DatabaseParams | None = None) -> list[DatabaseRow]:
        """Fetch rows from the database using ``query`` and optional params."""
        pass

    @abc.abstractmethod
    def close(self) -> None:
        """Close database resources held by the manager."""
