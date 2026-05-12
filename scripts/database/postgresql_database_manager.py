"""PostgreSQL implementation of the database manager interface."""

from __future__ import annotations

import collections.abc
import dataclasses
import logging
import os
import typing

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from scripts.database.database_manager import (
    DatabaseManager,
    DatabasePayload,
    DatabaseParams,
    DatabaseRow,
    DatabaseRequestType,
    DatabaseRows,
)
from scripts.database.schema_metadata_store import (
    ColumnMetadata,
    SchemaMetadataStore,
    TableSchemaMetadata,
)

POSTGRES_DSN_ENV_VAR = "POSTGRES_DSN"
LOGGER = logging.getLogger(__name__)


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


@dataclasses.dataclass
class PostgreSQLDatabaseManagerContext:
    autocommit: bool
    schema_metadata_store: SchemaMetadataStore | None
    logger: logging.Logger
    connection_kwargs: dict[str, typing.Any]

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "autocommit": self.autocommit,
            "schema_metadata_store": self.schema_metadata_store,
            "logger": self.logger,
            **self.connection_kwargs,
        }


class NormalizingRowsException(ValueError):
    def __init__(self, error_msg: str) -> None:
        super().__init__(error_msg)


class PostgreSQLDatabaseManager(DatabaseManager):
    """Database manager backed by a PostgreSQL connection."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
        autocommit: bool = False,
        schema_metadata_store: SchemaMetadataStore | None = None,
        logger: logging.Logger | None = None,
        **connection_kwargs: dict[str, typing.Any],
    ) -> None:
        """Create a PostgreSQL manager.

        Args:
            dsn: PostgreSQL connection string. If omitted, connection keyword
                arguments such as ``host``, ``port``, ``dbname``, ``user`` and
                ``password`` can be supplied.
            autocommit: Whether the connection should commit automatically.
            schema_metadata_store: Optional metadata store used to validate rows
                before inserting them.
            logger: Optional logger for rejected row messages.
            connection_kwargs: Additional arguments forwarded to psycopg.
        """
        self.schema_metadata_store: SchemaMetadataStore | None = schema_metadata_store
        self.logger: logging.Logger = logger or LOGGER
        self.connection: psycopg.Connection = psycopg.connect(
            dsn,
            autocommit=autocommit,
            row_factory=dict_row,
            **connection_kwargs,
        )

    @classmethod
    def create_from_env(
        cls, context: PostgreSQLDatabaseManagerContext, env_var: str = POSTGRES_DSN_ENV_VAR
    ) -> "PostgreSQLDatabaseManager":
        """Create a manager using a PostgreSQL DSN stored in an environment variable.

        By default this method reads ``POSTGRES_DSN``. The value must be a
        complete PostgreSQL connection string accepted by ``psycopg.connect``,
        for example::

            postgresql://postgres:postgres@localhost:5432/weather_operational

        This is the preferred constructor for Docker Compose and cloud
        deployments because the application can receive connection details from
        environment variables instead of hardcoding credentials in source code.

        Args:
            env_var: Name of the environment variable containing the PostgreSQL
                DSN. Defaults to ``POSTGRES_DSN``.

        Raises:
            ValueError: If the environment variable is missing or empty.

        Returns:
            A configured ``PostgreSQLDatabaseManager`` instance.
        """
        dsn: str = os.getenv(env_var, "").strip()
        if not dsn:
            raise ValueError(f"PostgreSQL DSN not found in environment variable {env_var}.")
        return cls(dsn, **context.to_dict())

    def fetch_table_metadata(self, table_name: str) -> TableSchemaMetadata | None:
        """Fetch cached table metadata from the configured schema metadata store.

        In production this is typically backed by Redis via
        ``RedisSchemaMetadataStore``. If no store is configured, or if Redis does
        not contain metadata for ``table_name``, ``None`` is returned and row
        validation can be skipped by the caller.
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
        sequence of row dictionaries. PostgreSQL insertion code is simpler and
        safer when it always receives one shape, so this helper turns a single
        mapping into ``[mapping]`` and turns a sequence into a plain ``list``.

        This is also the first defensive checkpoint in the write path. It
        rejects empty input, rejects non-mapping row objects, and rejects a row
        with no columns because none of those cases can produce a meaningful
        ``INSERT`` statement.
        """
        if isinstance(data, collections.abc.Mapping):
            rows = [data]
        else:
            rows = list(data)

        if not rows:
            raise NormalizingRowsException("At least one row is required to push data.")

        if not all(isinstance(row, collections.abc.Mapping) for row in rows):
            raise TypeError("Rows must be mappings of column names to values.")

        if not rows[0]:
            raise NormalizingRowsException("Rows must contain at least one column.")

        return rows

    def _filter_invalid_rows(
        self, schema: TableSchemaMetadata | None, rows: list[DatabaseRow]
    ) -> tuple[list[DatabaseRow], list[RejectedDatabaseRow]]:
        """Split normalized rows into rows that can be inserted and rejected rows.

        When cached schema metadata is available, each row is checked against
        the table definition before PostgreSQL sees it. A row is rejected if it
        contains a column that is not part of the table, or if it omits a
        required column. Required columns are columns that cannot be null and do
        not have a PostgreSQL default or identity value.

        If schema metadata is missing, the method returns all rows as valid and
        leaves final validation to PostgreSQL. That keeps ingestion working even
        when Redis metadata has not been warmed yet, while still giving us
        richer pre-insert logging when metadata exists.
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

    @staticmethod
    def _group_rows_by_columns(rows: list[DatabaseRow]) -> dict[tuple[str, ...], list[DatabaseRow]]:
        """Group rows that have the same columns in the same order.

        ``executemany`` runs one SQL statement repeatedly with different
        parameter values, so every row in one call must match the placeholders
        in that statement. Rows are grouped by their exact column tuple so that
        rows like ``{"city": ..., "temp": ...}`` and rows that include an
        extra optional column are inserted with separate SQL statements.

        Keeping separate groups also lets omitted optional columns stay omitted,
        which means PostgreSQL can apply defaults instead of us inserting
        explicit ``NULL`` values.
        """
        rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]] = {}
        for row in rows:
            columns: tuple[str, ...] = tuple(row.keys())
            rows_by_columns.setdefault(columns, []).append(row)
        return rows_by_columns

    def _prepare_payload_for_insert(
        self, table_name: str, data: DatabaseRows | DatabasePayload
    ) -> PreparedDatabasePayload:
        """Normalize incoming data and separate valid rows from rejected rows.

        This is the preparation stage for ``push_data``. It accepts either raw
        row input or a ``DatabasePayload``, normalizes that input into a payload
        whose ``data`` is always a list of row mappings, and then fetches cached
        table metadata for validation.

        The returned ``PreparedDatabasePayload`` keeps the original payload
        context, such as sender and creation time, together with two row lists:
        rows that are safe to attempt inserting and rows rejected before the
        database call. This keeps validation easy to test without opening a
        cursor or starting a transaction.
        """
        rows: list[DatabaseRow] = typing.cast(list[DatabaseRow], payload.data)
        payload: DatabasePayload = self._normalize_payload(data)
        schema: TableSchemaMetadata | None = self.fetch_table_metadata(table_name)
        valid_rows, rejected_rows = self._filter_invalid_rows(schema, rows)
        return PreparedDatabasePayload(
            payload=payload,
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
        )

    def _insert_valid_rows(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> int:
        """Insert all valid rows from a prepared payload in one transaction.

        This method owns the transaction boundary for the write. It groups valid
        rows by matching column sets, opens a cursor, delegates the actual
        grouped ``executemany`` calls to ``_insert_row_groups``, and commits
        only after all groups succeed.

        If any insert group fails, the whole transaction is rolled back so the
        table is not left with a partial payload. The exception is logged with
        payload context and then re-raised so callers can decide how to handle
        the failure.
        """
        rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]] = self._group_rows_by_columns(
            prepared_payload.valid_rows
        )

        try:
            with self.connection.cursor() as cursor:
                self._insert_row_groups(cursor, table_name, prepared_payload.payload, rows_by_columns)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            self._log_payload_insert_failed(table_name, prepared_payload)
            raise

        return len(prepared_payload.valid_rows)

    def _insert_row_groups(
        self,
        cursor: psycopg.Cursor,
        table_name: str,
        payload: DatabasePayload,
        rows_by_columns: dict[tuple[str, ...], list[DatabaseRow]],
    ) -> None:
        """Execute one batched insert per group of rows with matching columns.

        ``rows_by_columns`` is produced by ``_group_rows_by_columns``. Each key
        is the exact column tuple for one compatible group, and each value is
        the list of row mappings that can use that same ``INSERT`` statement.

        For every group this method logs what is about to be inserted, builds
        the matching parameterized query, and then calls ``executemany`` so
        psycopg can send the same statement with multiple parameter mappings.
        Transaction commit and rollback are handled by ``_insert_valid_rows``;
        this helper only performs the grouped cursor operations.
        """
        for columns, grouped_rows in rows_by_columns.items():
            self._log_row_group_insert(table_name, payload, columns, grouped_rows)
            cursor.executemany(self._build_insert_query(table_name, columns), grouped_rows)

    def _build_insert_query(self, table_name: str, columns: tuple[str, ...]) -> sql.Composable:
        """Build the parameterized PostgreSQL ``INSERT`` query for one column group.

        The table name and column names are SQL identifiers, not data values, so
        they cannot be passed through the normal parameter dictionary used by
        ``executemany``. Psycopg's ``sql.Identifier`` quotes those names safely
        and handles schema-qualified table names through ``_table_identifier``.

        The values are represented with named placeholders matching each column
        name, for example ``%(city)s``. That lets ``executemany`` bind every row
        mapping directly to the generated statement without string-formatting
        the actual row values into SQL.
        """
        return sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values})").format(
            table=self._table_identifier(table_name),
            columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            values=sql.SQL(", ").join(sql.Placeholder(column) for column in columns),
        )

    def push_data(self, table_name: str, data: DatabaseRows | DatabasePayload) -> int:
        """Validate and insert one or more rows into a PostgreSQL table.

        ``data`` can be either a single mapping or a sequence of mappings. Each
        mapping represents one database row, where keys are column names and
        values are the values to insert, for example::

            {
                "city": "Warsaw",
                "temperature": 18.5,
                "measured_at": datetime.datetime(...),
            }

        Before writing to PostgreSQL, rows are normalized into a list and
        validated against table metadata. Invalid rows are not inserted and are
        logged with the reason for rejection. Valid rows are grouped by their
        exact column set before insertion, which allows rows that omit optional
        columns to keep PostgreSQL defaults instead of forcing explicit
        ``NULL`` values.

        The method commits the transaction after all grouped inserts succeed.
        If any insert fails, the transaction is rolled back and the original
        exception is re-raised.

        Args:
            table_name: Target table name. It can be unqualified, such as
                ``weather_observations``, or schema-qualified, such as
                ``public.weather_observations``.
            data: A row mapping or a sequence of row mappings to insert.

        Raises:
            ValueError: If no rows are provided or a row has no columns.
            TypeError: If ``data`` contains values that are not mappings.
            psycopg.Error: If PostgreSQL rejects the generated insert query.

        Returns:
            Number of rows accepted for insertion.
        """

        prepared_payload: PreparedDatabasePayload = self._prepare_payload_for_insert(table_name, data)
        self._log_payload_received(table_name, prepared_payload.payload)
        self._log_rejected_rows(table_name, prepared_payload.rejected_rows)

        if not prepared_payload.valid_rows:
            self._log_no_valid_rows(table_name, prepared_payload)
            return 0

        inserted_rows: int = self._insert_valid_rows(table_name, prepared_payload)
        self._log_payload_inserted(table_name, prepared_payload)
        return inserted_rows

    def cache_table_schema(self, table_name: str) -> TableSchemaMetadata:
        """Fetch table schema from PostgreSQL and cache it in the metadata store.

        This method warms the schema cache used by ``push_data`` validation. It
        reads column definitions from PostgreSQL's ``information_schema`` for
        the requested table, converts each column into ``ColumnMetadata``, and
        stores the resulting ``TableSchemaMetadata`` through the configured
        ``SchemaMetadataStore``. In the normal deployment that store is backed
        by Redis, so later inserts can validate rows without querying
        PostgreSQL's catalog every time.

        The cached fields are the pieces needed to decide whether incoming rows
        are structurally valid before insert: column name, PostgreSQL data type,
        nullability, whether a default exists, and whether the column is an
        identity column. Those values drive checks for unknown columns and
        missing required columns.

        Args:
            table_name: Table to inspect. It can be unqualified, such as
                ``weather_observations``, or schema-qualified, such as
                ``public.weather_observations``.

        Raises:
            ValueError: If no schema metadata store is configured, or if the
                table cannot be found in PostgreSQL's ``information_schema``.

        Returns:
            The schema metadata object that was written to the metadata store.
        """
        if self.schema_metadata_store is None:
            raise ValueError("Schema metadata store is not configured.")

        schema_name, short_table_name = self._split_table_name(table_name)
        rows = self.fetch_data(
            """
            SELECT column_name, data_type, is_nullable, column_default, is_identity
            FROM information_schema.columns
            WHERE table_schema = %(schema_name)s
              AND table_name = %(table_name)s
            ORDER BY ordinal_position
            """,
            {"schema_name": schema_name, "table_name": short_table_name},
        )
        if not rows:
            raise ValueError(f"Table schema not found for {table_name}.")

        schema = TableSchemaMetadata(
            table_name=table_name,
            columns=tuple(
                ColumnMetadata(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    is_nullable=row["is_nullable"] == "YES",
                    has_default=row["column_default"] is not None,
                    is_identity=row["is_identity"] == "YES",
                )
                for row in rows
            ),
        )
        self.schema_metadata_store.set_table_schema(schema)
        return schema

    def fetch_data(self, query: str, params: DatabaseParams | None = None) -> list[DatabaseRow]:
        """Run a read query and return result rows as dictionaries.

        The manager connection is configured with psycopg's ``dict_row`` row
        factory, so every returned row behaves like a mapping from column name
        to value. That makes callers such as ``cache_table_schema`` easier to
        read because they can access ``row["column_name"]`` instead of relying
        on tuple positions.

        ``params`` should be used for dynamic values instead of formatting them
        into the SQL string. Psycopg will bind those parameters safely when
        executing the query.

        Args:
            query: SQL read query to execute.
            params: Optional sequence or mapping of parameters for the query.

        Returns:
            A list of row mappings. If the query returns no rows, the list is
            empty.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return list(cursor.fetchall())

    def close(self) -> None:
        """Close the PostgreSQL connection."""
        self.connection.close()

    def __enter__(self) -> "PostgreSQLDatabaseManager":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: typing.Any,
    ) -> None:
        self.close()

    def _log_payload_received(self, table_name: str, payload: DatabasePayload) -> None:
        self.logger.info(
            "Processing database payload: request_type=%s sender=%s table=%s rows=%s created_at=%s",
            payload.request_type,
            payload.sender,
            table_name,
            payload.n_rows,
            payload.created_at.isoformat(),
        )

    def _log_rejected_rows(self, table_name: str, rejected_rows: list[RejectedDatabaseRow]) -> None:
        for rejected_row in rejected_rows:
            self.logger.warning(
                "Rejected row for table %s before insert: %s. Row: %s",
                table_name,
                rejected_row.reason,
                rejected_row.row,
            )

    def _log_no_valid_rows(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> None:
        self.logger.warning(
            "No valid rows to insert for table %s: sender=%s submitted=%s rejected=%s",
            table_name,
            prepared_payload.payload.sender,
            prepared_payload.payload.n_rows,
            len(prepared_payload.rejected_rows),
        )

    def _log_row_group_insert(
        self,
        table_name: str,
        payload: DatabasePayload,
        columns: tuple[str, ...],
        grouped_rows: list[DatabaseRow],
    ) -> None:
        self.logger.info(
            "Inserting row group into %s: sender=%s rows=%s columns=%s",
            table_name,
            payload.sender,
            len(grouped_rows),
            columns,
        )

    def _log_payload_insert_failed(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> None:
        self.logger.exception(
            "Failed to insert database payload: sender=%s table=%s valid_rows=%s rejected_rows=%s",
            prepared_payload.payload.sender,
            table_name,
            len(prepared_payload.valid_rows),
            len(prepared_payload.rejected_rows),
        )

    def _log_payload_inserted(self, table_name: str, prepared_payload: PreparedDatabasePayload) -> None:
        self.logger.info(
            "Inserted database payload: sender=%s table=%s inserted=%s rejected=%s",
            prepared_payload.payload.sender,
            table_name,
            len(prepared_payload.valid_rows),
            len(prepared_payload.rejected_rows),
        )

    @classmethod
    def _normalize_payload(cls, data: DatabaseRows | DatabasePayload) -> DatabasePayload:
        payload = data if isinstance(data, DatabasePayload) else DatabasePayload(data=data)
        rows = cls._normalize_rows(payload.data)
        n_rows = len(rows)

        if payload.n_rows is not None and payload.n_rows != n_rows:
            raise NormalizingRowsException(
                f"Payload row count mismatch: n_rows={payload.n_rows}, actual_rows={n_rows}."
            )
        if payload.request_type != DatabaseRequestType.PUSH_DATA:
            raise NormalizingRowsException(f"Unsupported database request type: {payload.request_type}.")

        return dataclasses.replace(payload, data=rows, n_rows=n_rows)

    @staticmethod
    def _table_identifier(table_name: str) -> sql.Identifier:
        table_parts = [part.strip() for part in table_name.split(".") if part.strip()]
        if not table_parts:
            raise ValueError("Table name cannot be empty.")
        return sql.Identifier(*table_parts)

    @staticmethod
    def _split_table_name(table_name: str) -> tuple[str, str]:
        table_parts = [part.strip() for part in table_name.split(".") if part.strip()]
        if len(table_parts) == 1:
            return "public", table_parts[0]
        if len(table_parts) == 2:
            return table_parts[0], table_parts[1]
        raise ValueError("Table name can contain at most schema and table parts.")
