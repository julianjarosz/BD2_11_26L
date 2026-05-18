from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
from datetime import UTC, datetime
from scripts.database.models.database_types import DatabaseRow, DatabaseRequestType


@dataclass(frozen=True, slots=True)
class DatabasePayload:
    """
    Database payload providing data (rows) & metadata about transaction for logging.

    Parameters:
        rows: Iterable of DatabaseRow objects.
        number_of_rows: Number of rows in the payload.
        created_at: Timestamp of the payload creation.
        request_type: Type of the request that created the payload.
    """

    rows: Iterable[DatabaseRow]
    number_of_rows: int
    request_type: DatabaseRequestType
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
