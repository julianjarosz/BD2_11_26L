from typing import Any, Mapping, Protocol

Row = Mapping[str, Any]


class Source(Protocol):
    """Interface for data source in the pipeline"""

    name: str

    def extract(self, resource_name: str) -> list[Row]:
        ...
