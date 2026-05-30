from __future__ import annotations

import dataclasses
import typing

from scripts.database.cleaners.data_schema_cleaner import DataSchemaCleaner
from scripts.database.managers.base import DatabaseManagerLoggerInterface
from scripts.database.stores.schema_metadata_store import SchemaMetadataStore


@dataclasses.dataclass
class PostgreSQLDatabaseManagerContext:
    autocommit: bool
    schema_metadata_store: SchemaMetadataStore | None
    data_schema_cleaner: DataSchemaCleaner | None
    connection_kwargs: dict[str, typing.Any]
    database_logger: DatabaseManagerLoggerInterface | None = None

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "autocommit": self.autocommit,
            "schema_metadata_store": self.schema_metadata_store,
            "data_schema_cleaner": self.data_schema_cleaner,
            "database_logger": self.database_logger,
            **self.connection_kwargs,
        }
