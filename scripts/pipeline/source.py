from typing import Any, Mapping, Protocol

Row = Mapping[str, Any]
"""Single extracted row represented as a mapping of column names to values."""


class Source(Protocol):
    """Interface for data sources used by the ELT pipeline.

    A source knows how to extract rows from a named resource, such as a table,
    endpoint, or file. Pipeline load steps reference sources by ``name``.
    """

    name: str
    """Source identifier referenced by ``LoadStep.source_name``."""

    def extract(self, resource_name: str) -> list[Row]:
        """Extract rows from a named source resource.

        Args:
            resource_name: Resource identifier understood by the source.

        Returns:
            Extracted rows as mappings of column names to values.
        """
        raise NotImplementedError
