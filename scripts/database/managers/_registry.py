"""Default database manager registrations."""

from __future__ import annotations

from scripts.database.managers.base import DatabaseManagerInterface
from scripts.database.managers.factory import DatabaseManagerFactory, DatabaseManagerType
from scripts.database.managers.postgresql import PostgreSQLDatabaseManager


def register_database_manager(
    manager_type: str | DatabaseManagerType,
    manager_cls: type[DatabaseManagerInterface],
) -> None:
    """Register or refresh one database manager mapping."""
    try:
        DatabaseManagerFactory.register(manager_type, manager_cls)
    except ValueError:
        DatabaseManagerFactory.update(manager_type, manager_cls)


def register_database_managers() -> None:
    """Register default database manager implementations."""
    register_database_manager(DatabaseManagerType.POSTGRESQL, PostgreSQLDatabaseManager)
    register_database_manager("postgres", PostgreSQLDatabaseManager)
    register_database_manager("pg", PostgreSQLDatabaseManager)


register_database_managers()
