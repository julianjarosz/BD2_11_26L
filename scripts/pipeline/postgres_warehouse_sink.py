from scripts.database.database_manager import DatabaseManager
from scripts.pipeline.source import Row
from scripts.pipeline.transformation import Transformation


class PostgresWarehouseSink:
    def __init__(
        self,
        name: str,
        database: DatabaseManager,
        transformations: list[Transformation]
    ) -> None:
        self.name = name
        self.database = database
        self.transformations = transformations

    def clear_staging(self, staging_table: str) -> None:
        self.database.execute(f"TRUNCATE TABLE {staging_table}")

    def load_staging(self, staging_table: str, rows: list[Row]) -> int:
        if not rows:
            return 0

        return self.database.push_data(staging_table, rows)

    def run_transformations(self) -> None:
        for transformation in self.transformations:
            transformation.run(self.database)
