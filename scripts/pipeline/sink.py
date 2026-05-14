from typing import Any, Mapping, Protocol

Row = Mapping[str, Any]


class Sink(Protocol):
    name: str

    def clear_staging(self, staging_table: str) -> None:
        ...

    def load_staging(self, staging_table: str, rows: list[Row]) -> int:
        ...

    def run_transformations(self) -> None:
        ...
