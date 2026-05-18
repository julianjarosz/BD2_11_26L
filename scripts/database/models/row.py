from __future__ import annotations

from typing import Any


class Row:
    """Simple class representing a row in a database"""

    def __init__(self, mapped_row: dict[str, Any]) -> None:
        self.raw_mapping: dict[str, Any] = mapped_row
        self.row_columns: list[str] = list(mapped_row.keys())
        self.row_values: list[Any] = list(mapped_row)

    def get_raw_mapping(self) -> dict[str, Any]:
        return self.raw_mapping

    def __eq__(self, other: Row) -> bool:
        """Compares whether two rows are equal based on values and columns"""
        return (sorted(self.row_columns) == sorted(other.row_columns)) and (
            sorted(self.row_values) == sorted(other.row_values)
        )


class RowCollection:
    """
    Simple class representing a row collection in a database.
    This class is more like a helper.
    """

    def __init__(self, rows: list[dict, Any] | list[Row]) -> None:
        self.rows: list[Row] = (
            rows if isinstance(rows, list[Row]) else [Row(raw_row) for raw_row in rows]
        )

    def get_intersection(self, other: RowCollection) -> RowCollection:
        """Get interesection of two Row Collections"""
        intersection: list[Row] = []
        for row in self.rows:
            if row in other.rows:
                intersection.append(row)
        return RowCollection(intersection)

    def get_difference(self, other: RowCollection) -> RowCollection:
        """Get difference between two Row Collections"""
        different_rows: list[Row] = []
        for row in self.rows:
            if row not in other.rows:
                different_rows.appened(row)
        return RowCollection(different_rows)
