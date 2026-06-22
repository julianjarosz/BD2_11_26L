from __future__ import annotations

import pytest

from scripts.database.managers.base.tools.payload_normalizer import DatabasePayloadNormalizer
from scripts.database.managers.base.tools.schema_validator import TableSchemaRowValidator
from scripts.database.models.database_payload import DatabasePayload
from scripts.database.models.database_types import DatabaseRequestType
from scripts.database.stores.schema_metadata_store import ColumnMetadata, TableSchemaMetadata
from scripts.errors.database_errors import NormalizingRowsException


def test_schema_validator_accepts_valid_rows_and_rejects_unknown_or_missing_columns() -> None:
    schema = TableSchemaMetadata(
        table_name="weather",
        columns=(
            ColumnMetadata(name="id", is_nullable=False),
            ColumnMetadata(name="name", is_nullable=False),
            ColumnMetadata(name="created_at", is_nullable=False, has_default=True),
            ColumnMetadata(name="note", is_nullable=True),
        ),
    )
    rows = [
        {"id": 1, "name": "Warsaw"},
        {"id": 2, "name": "Krakow", "unexpected": "value"},
        {"id": 3, "note": "missing required name"},
    ]

    valid_rows, rejected_rows = TableSchemaRowValidator().validate(schema, rows)

    assert valid_rows == [rows[0]]
    assert [rejected.row for rejected in rejected_rows] == [rows[1], rows[2]]
    assert rejected_rows[0].reason == "unknown columns: unexpected"
    assert rejected_rows[1].reason == "missing required columns: name"


def test_schema_validator_treats_empty_column_names_as_unknown_columns() -> None:
    schema = TableSchemaMetadata(
        table_name="weather",
        columns=(
            ColumnMetadata(name="id", is_nullable=False),
            ColumnMetadata(name="name", is_nullable=False),
        ),
    )
    row = {"id": 1, "name": "Warsaw", "": "empty column name"}

    valid_rows, rejected_rows = TableSchemaRowValidator().validate(schema, [row])

    assert valid_rows == []
    assert [rejected.row for rejected in rejected_rows] == [row]
    assert rejected_rows[0].reason.startswith("unknown columns")


def test_schema_validator_accepts_all_rows_when_schema_is_not_available() -> None:
    rows = [{"unknown": "accepted without schema metadata"}]

    valid_rows, rejected_rows = TableSchemaRowValidator().validate(None, rows)

    assert valid_rows == rows
    assert not rejected_rows


def test_payload_normalizer_wraps_single_mapping_into_insert_payload() -> None:
    payload = DatabasePayloadNormalizer.normalize_payload({"id": 1, "name": "Warsaw"})

    assert payload.rows == [{"id": 1, "name": "Warsaw"}]
    assert payload.number_of_rows == 1
    assert payload.request_type == DatabaseRequestType.INSERT_DATA


def test_payload_normalizer_rebuilds_existing_payload_with_normalized_rows() -> None:
    original = DatabasePayload(
        rows=({"id": 1}, {"id": 2}),
        number_of_rows=2,
        request_type=DatabaseRequestType.INSERT_DATA,
    )

    normalized = DatabasePayloadNormalizer.normalize_payload(original)

    assert normalized.rows == [{"id": 1}, {"id": 2}]
    assert normalized.number_of_rows == 2
    assert normalized.request_type == DatabaseRequestType.INSERT_DATA
    assert normalized.created_at == original.created_at


@pytest.mark.parametrize("data", [[], (), {}, [{}]])
def test_payload_normalizer_rejects_empty_inputs_or_empty_rows(data: object) -> None:
    with pytest.raises(NormalizingRowsException):
        DatabasePayloadNormalizer.normalize_payload(data)  # type: ignore[arg-type]


def test_payload_normalizer_rejects_non_mapping_rows() -> None:
    with pytest.raises(TypeError, match="Rows must be mappings"):
        DatabasePayloadNormalizer.normalize_payload([object()])  # type: ignore[list-item]


def test_payload_normalizer_rejects_row_count_mismatch() -> None:
    payload = DatabasePayload(
        rows=[{"id": 1}],
        number_of_rows=2,
        request_type=DatabaseRequestType.INSERT_DATA,
    )

    with pytest.raises(NormalizingRowsException, match="Payload row count mismatch"):
        DatabasePayloadNormalizer.normalize_payload(payload)


def test_payload_normalizer_rejects_unsupported_request_type() -> None:
    payload = DatabasePayload(
        rows=[{"id": 1}],
        number_of_rows=1,
        request_type=DatabaseRequestType.UPDATE_DATA,
    )

    with pytest.raises(NormalizingRowsException, match="Unsupported database request type"):
        DatabasePayloadNormalizer.normalize_payload(payload)
