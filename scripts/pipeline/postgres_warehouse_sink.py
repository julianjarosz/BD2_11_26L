"""PostgreSQL warehouse sink for staging loads and transformations."""

from scripts.database.database_manager import DatabaseManager
from scripts.errors.pipeline_errors import PostgresWarehouseSinkError
from scripts.pipeline.source import Row
from scripts.pipeline.transformation import Transformation


class PostgresWarehouseSink:
    """Load extracted rows into PostgreSQL staging tables.

    The sink name is used by ``LoadStep.sink_name`` to connect configured load
    steps to this sink. Staging tables are cleared and loaded through the
    database manager, and transformations are executed after staging loads.
    """

    def __init__(
        self,
        name: str,
        database: DatabaseManager,
        transformations: list[Transformation],
    ) -> None:
        """Create a PostgreSQL warehouse sink.

        Args:
            name: Sink identifier referenced by pipeline load steps.
            database: Database manager used to write staging rows and run SQL.
            transformations: Transformations to run after staging is loaded.
        """
        self.name = name
        self.database = database
        self.transformations = transformations

    def clear_staging(self, staging_table: str) -> None:
        """Remove all rows from a staging table.

        Args:
            staging_table: Staging table to truncate.

        Raises:
            PostgresWarehouseSinkError: If the truncate operation fails.
        """
        try:
            self.database.execute(f"TRUNCATE TABLE {staging_table}")
        except Exception as exc:
            raise PostgresWarehouseSinkError(
                f"Failed to clear staging table {staging_table!r} "
                f"for sink {self.name!r}: {exc}"
            ) from exc

    def load_staging(self, staging_table: str, rows: list[Row]) -> int:
        """Load rows into a staging table.

        Args:
            staging_table: Staging table to load.
            rows: Rows to insert into the staging table.

        Returns:
            Number of rows submitted to the database.

        Raises:
            PostgresWarehouseSinkError: If the load operation fails.
        """
        if not rows:
            return 0

        try:
            return self.database.push_data(staging_table, rows)
        except Exception as exc:
            raise PostgresWarehouseSinkError(
                f"Failed to load staging table {staging_table!r} "
                f"for sink {self.name!r}: {exc}"
            ) from exc

    def run_transformations(self) -> None:
        """Run configured transformations against the warehouse database.

        Raises:
            PostgresWarehouseSinkError: If a transformation fails.
        """
        for transformation in self.transformations:
            try:
                transformation.run(self.database)
            except Exception as exc:
                raise PostgresWarehouseSinkError(
                    f"Failed to run transformation {transformation.name!r} "
                    f"for sink {self.name!r}: {exc}"
                ) from exc
