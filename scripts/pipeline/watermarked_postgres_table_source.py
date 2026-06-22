from scripts.database.managers.base import DatabaseManagerInterface
from scripts.errors.pipeline_errors import PostgresTableSourceError
from scripts.pipeline.source import Row


class WatermarkedPostgresTableSource:
    """Extract rows from operational tables using watermarks stored in warehouse."""

    def __init__(
        self,
        name: str,
        operational_database: DatabaseManagerInterface,
        warehouse_database: DatabaseManagerInterface,
        id_columns: dict[str, str],
        full_load_tables: set[str] | None = None,
    ) -> None:
        self.name = name
        self.operational_database = operational_database
        self.warehouse_database = warehouse_database
        self.id_columns = id_columns
        self.full_load_tables = full_load_tables or set()

    def extract(self, resource_name: str) -> list[Row]:
        if resource_name not in self.id_columns:
            raise PostgresTableSourceError(
                f"Table {resource_name!r} is not configured for watermarked extraction."
            )

        id_column = self.id_columns[resource_name]
        source_name = f"operational.{resource_name}"

        try:
            if resource_name in self.full_load_tables:
                result = self.operational_database.fetch_data(f"""
                    SELECT *
                    FROM {resource_name}
                    ORDER BY {id_column}
                    """)
                return list(result.successful_rows)

            watermark_result = self.warehouse_database.fetch_data(f"""
                SELECT COALESCE(last_loaded_id, 0) AS last_loaded_id
                FROM dw.etl_watermark
                WHERE source_name = '{source_name}'
                """)
            if watermark_result.successful_rows:
                last_loaded_id = watermark_result.successful_rows[0]["last_loaded_id"]
            else:
                last_loaded_id = 0

            result = self.operational_database.fetch_data(f"""
                SELECT *
                FROM {resource_name}
                WHERE {id_column} > {int(last_loaded_id)}
                ORDER BY {id_column}
                """)
            return list(result.successful_rows)
        except Exception as exc:
            raise PostgresTableSourceError(
                f"Failed to extract new rows from table {resource_name!r} "
                f"for source {self.name!r}: {exc}"
            ) from exc
