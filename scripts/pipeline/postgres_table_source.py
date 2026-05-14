from scripts.database.database_manager import DatabaseManager
from source import Row


class PostgresTableSource:
    def __init__(self, name: str, database: DatabaseManager) -> None:
        self.name = name
        self.database = database

    def extract(self, resource_name: str) -> list[Row]:
        return self.database.fetch_data(f"SELECT * FROM {resource_name}")
