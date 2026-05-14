from typing import Protocol
from scripts.database.database_manager import DatabaseManager


class Transformation(Protocol):
    name: str

    def run(self, database: DatabaseManager) -> None:
        ...
