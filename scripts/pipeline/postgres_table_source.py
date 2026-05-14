"""PostgreSQL table-backed source for the ELT pipeline."""

from scripts.database.database_manager import DatabaseManager
from scripts.errors.pipeline_errors import PostgresTableSourceError
from scripts.pipeline.source import Row


class PostgresTableSource:
    """Extract rows from PostgreSQL tables through a database manager.
    x
        The source name is used by ``LoadStep.source_name`` to connect configured
        load steps to this source. ``resource_name`` values passed to
        :meth:`extract` are treated as table names.
    """

    def __init__(self, name: str, database: DatabaseManager) -> None:
        """Create a PostgreSQL table source.

        Args:
            name: Source identifier referenced by pipeline load steps.
            database: Database manager used to execute extract queries.
        """
        self.name = name
        self.database = database

    def extract(self, resource_name: str) -> list[Row]:
        """Fetch all rows from a PostgreSQL table.

        Args:
            resource_name: Table name to extract from.

        Returns:
            Rows fetched from the requested table.

        Raises:
            PostgresTableSourceError: If the database query fails.
        """
        try:
            return self.database.fetch_data(f"SELECT * FROM {resource_name}")
        except Exception as exc:
            raise PostgresTableSourceError(
                f"Failed to extract table {resource_name!r} "
                f"from source {self.name!r}: {exc}"
            ) from exc
