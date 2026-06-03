"""Transformation protocol for post-load pipeline steps."""

from typing import Protocol

from scripts.database.managers.base import DatabaseManagerInterface


class Transformation(Protocol):
    """Interface for transformations run after staging loads complete.

    Transformations receive a database manager so they can execute SQL or other
    warehouse-side operations. Sinks run configured transformations by name and
    order.
    """

    name: str
    """Transformation identifier used in logs, warnings, and errors."""

    def run(self, database: DatabaseManagerInterface) -> None:
        """Run the transformation using the provided database manager.

        Args:
            database: Database manager connected to the transformation target.
        """
        ...
