"""Base implementation of the database manager interface with shared validation and logging."""

from __future__ import annotations

import collections.abc
import dataclasses
import logging
import typing

from scripts.database.database_manager import (
    DatabaseManager,
    DatabasePayload,
    DatabaseRequestType,
    DatabaseRow,
    DatabaseRows,
)
from scripts.database.schema_metadata_store import (
    SchemaMetadataStore,
    TableSchemaMetadata,
)
from scripts.errors.database_errors import NormalizingRowsException


@dataclasses.dataclass(frozen=True, slots=True)
class RejectedDatabaseRow:
    """Row rejected before insertion and the reason why."""

    row: DatabaseRow
    reason: str


@dataclasses.dataclass(frozen=True, slots=True)
class PreparedDatabasePayload:
    """Normalized and validated payload ready for insertion."""

    payload: DatabasePayload
    valid_rows: list[DatabaseRow]
    rejected_rows: list[RejectedDatabaseRow]


class BaseDatabaseManager(DatabaseManager):
    """Abstract base class implementing shared database manager functionality.

    This class provides common validation, normalization, and logging methods
    shared by concrete implementations like PostgreSQLDatabaseManager and
    RedisDatabaseManager. It handles:

    - Row data normalization and validation
    - Schema metadata fetching and caching
    - Payload preparation and filtering
    - Comprehensive logging at each operation stage
    - Context manager protocol
    """

    schema_metadata_store: SchemaMetadataStore | None
    logger: logging.Logger

    def __init__(
        self,
        *,
        schema_metadata_store: SchemaMetadataStore | None = None,
        logger: logging.Logger | None = None,
        default_logger: logging.Logger | None = None,
    ) -> None:
        """Initialize dependencies shared by concrete database managers."""
        self.schema_metadata_store = schema_metadata_store
        self.logger = logger or default_logger or logging.getLogger(self.__class__.__module__)

    def fetch_table_metadata(self, table_name: str) -> TableSchemaMetadata | None:
        """Fetch cached table metadata from the configured schema metadata store.

        If no store is configured, or if the metadata does not contain
        information for ``table_name``, ``None`` is returned and row validation
        can be skipped by the caller.

        Args:
            table_name: The name of the table to fetch metadata for.

        Returns:
            Table schema metadata if available, None otherwise.
        """
        if self.schema_metadata_store is None:
            self.logger.warning(
                "Schema metadata store is not configured. Skipping row validation for table %s.",
                table_name,
            )
            return None

        schema: TableSchemaMetadata | None = self.schema_metadata_store.get_table_schema(table_name)
        if schema is None:
            self.logger.warning(
                "Schema metadata for table %s was not found. Skipping row validation.",
                table_name,
            )
        return schema

    @staticmethod
    def _normalize_rows(data: DatabaseRows) -> list[DatabaseRow]:
        """Convert accepted input shapes into one non-empty list of row mappings.

        ``push_data`` lets callers pass either a single row dictionary or a
        sequence of row dictionaries. This helper turns a single mapping into
        ``[mapping]`` and turns a sequence into a plain ``list``.

        This is also the first defensive checkpoint in the write path. It
        rejects empty input, rejects non-mapping row objects, and rejects a row
        with no columns because none of those cases can produce a meaningful
        database operation.

        Args:
            data: Either a single row mapping or a sequence of row mappings.

        Raises:
            NormalizingRowsException: If rows are empty or have no columns.
            TypeError: If data contains non-mapping values.

        Returns:
            A list of row mappings.
        """
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

    def _filter_invalid_rows(
        self, schema: TableSchemaMetadata | None, rows: list[DatabaseRow]
    ) -> tuple[list[DatabaseRow], list[RejectedDatabaseRow]]:
        """Split normalized rows into valid rows and rejected rows.

        When cached schema metadata is available, each row is checked against
        the table definition. A row is rejected if it contains a column that is
        not part of the table, or if it omits a required column. Required
        columns are columns that cannot be null and do not have a default value.

        If schema metadata is missing, all rows are returned as valid.

        Args:
            schema: Table schema metadata, or None if unavailable.
            rows: List of normalized row mappings to validate.

        Returns:
            A tuple of (valid_rows, rejected_rows).
        """
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
                        reason=("missing required columns: " f"{', '.join(sorted(missing_required_columns))}"),
                    )
                )
                continue

            valid_rows.append(row)

        return valid_rows, rejected_rows

    def _prepare_payload_for_operation(
        self, table_name: str, data: DatabaseRows | DatabasePayload
    ) -> PreparedDatabasePayload:
        """Normalize incoming data and separate valid rows from rejected rows.

        This preparation stage accepts either raw row input or a
        ``DatabasePayload``, normalizes that input into a payload whose ``data``
        is always a list of row mappings, and then fetches cached table metadata
        for validation.

        The returned ``PreparedDatabasePayload`` keeps the original payload
        context together with two row lists: rows safe to process and rows
        rejected before the database/cache operation.

        Args:
            table_name: The target table name.
            data: Row data or DatabasePayload to process.

        Returns:
            A prepared payload with separated valid and rejected rows.
        """
        payload: DatabasePayload = self._normalize_payload(data)
        rows: list[DatabaseRow] = typing.cast(list[DatabaseRow], payload.data)
        schema: TableSchemaMetadata | None = self.fetch_table_metadata(table_name)
        valid_rows, rejected_rows = self._filter_invalid_rows(schema, rows)
        return PreparedDatabasePayload(
            payload=payload,
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
        )

    def _log_payload_received(self, table_name: str, payload: DatabasePayload) -> None:
        """Log receipt of a database payload."""
        self.logger.info(
            "Processing database payload: request_type=%s sender=%s table=%s rows=%s created_at=%s",
            payload.request_type,
            payload.sender,
            table_name,
            payload.n_rows,
            payload.created_at.isoformat(),
        )

    def _log_rejected_rows(self, table_name: str, rejected_rows: list[RejectedDatabaseRow]) -> None:
        """Log details of rejected rows."""
        for rejected_row in rejected_rows:
            self.logger.warning(
                "Rejected row for table %s: %s. Row: %s",
                table_name,
                rejected_row.reason,
                rejected_row.row,
            )

    def _log_no_valid_rows(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> None:
        """Log when no valid rows are available for processing."""
        self.logger.warning(
            "No valid rows to process for table %s: sender=%s submitted=%s rejected=%s",
            table_name,
            prepared_payload.payload.sender,
            prepared_payload.payload.n_rows,
            len(prepared_payload.rejected_rows),
        )

    @classmethod
    def _normalize_payload(cls, data: DatabaseRows | DatabasePayload) -> DatabasePayload:
        """Normalize and validate a database payload.

        Args:
            data: Either raw row data or a DatabasePayload instance.

        Returns:
            A normalized DatabasePayload with row count validated.

        Raises:
            NormalizingRowsException: If payload validation fails.
        """
        payload: DatabasePayload = data if isinstance(data, DatabasePayload) else DatabasePayload(data=data)
        rows: list[DatabaseRows] = cls._normalize_rows(payload.data)
        n_rows: int = len(rows)

        if payload.n_rows is not None and payload.n_rows != n_rows:
            raise NormalizingRowsException(
                f"Payload row count mismatch: n_rows={payload.n_rows}, actual_rows={n_rows}."
            )
        if payload.request_type != DatabaseRequestType.PUSH_DATA:
            raise NormalizingRowsException(f"Unsupported database request type: {payload.request_type}.")

        return dataclasses.replace(payload, data=rows, n_rows=n_rows)

    def __enter__(self) -> "BaseDatabaseManager":
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: typing.Any,
    ) -> None:
        """Exit context manager and close the connection."""
        self.close()

    def close(self) -> None:
        """Close the database/cache connection. Must be implemented by subclasses."""
        raise NotImplementedError
