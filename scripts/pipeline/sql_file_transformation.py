from pathlib import Path

from scripts.database.managers.database_manager import DatabaseManagerInterface


class SqlFileTransformation:
    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path

    def run(self, database: DatabaseManagerInterface) -> None:
        sql = self.path.read_text(encoding="utf-8")
        database.execute(sql)
