"""Sink protocol for pipeline loaders and transformations."""

from typing import Any, Mapping, Protocol

Row = Mapping[str, Any]
"""Single row represented as a mapping of column names to values."""


class Sink(Protocol):
    """Interface for destinations used by the ELT pipeline.

    A sink knows how to clear staging tables, load extracted rows into staging,
    and run transformations after staging data has been loaded. Pipeline load
    steps reference sinks by ``name``.
    """

    name: str
    """Sink identifier referenced by ``LoadStep.sink_name``."""

    def clear_staging(self, staging_table: str) -> None:
        """Clear a staging table before loading rows.

        Args:
            staging_table: Staging table to clear.
        """
        ...

    def load_staging(self, staging_table: str, rows: list[Row]) -> int:
        """Load rows into a staging table.

        Args:
            staging_table: Staging table to load.
            rows: Rows to write to staging.

        Returns:
            Number of rows submitted to the sink.
        """
        ...

    def run_transformations(self) -> None:
        """Run sink-specific transformations after staging loads complete."""
        ...
