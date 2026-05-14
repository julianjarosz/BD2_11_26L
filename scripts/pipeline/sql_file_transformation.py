from pathlib import Path
from scripts.database.database_manager import DatabaseManager


class SqlFileTransformation:
    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path

    def run(self, database: DatabaseManager) -> None:
        sql = self.path.read_text(encoding="utf-8")
        database.execute(sql)
