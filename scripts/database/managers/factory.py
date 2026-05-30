"""Factory helpers for constructing database managers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, final

from scripts.database.managers.base import DatabaseManagerInterface
from scripts.database.managers.postgresql import PostgreSQLDatabaseManager


class DatabaseManagerType(StrEnum):
    POSTGRESQL = "postgresql"


@final
class DatabaseManagerFactory:
    """Create concrete database managers from a requested backend type."""

    _FACTORY_REGISTRY: dict[str, type[DatabaseManagerInterface]] = {}

    @staticmethod
    def _normalize_manager_type(manager_type: str | DatabaseManagerType) -> str:
        if isinstance(manager_type, DatabaseManagerType):
            return manager_type.value

        return manager_type.strip().lower()

    @classmethod
    def register(
        cls, manager_type: str | DatabaseManagerType, manager_cls: type[DatabaseManagerInterface]
    ) -> None:
        normalized_key: str = cls._normalize_manager_type(manager_type)
        if normalized_key in cls._FACTORY_REGISTRY:
            raise ValueError("Manager with provided key already registered in factory registry!")
        cls._FACTORY_REGISTRY[normalized_key] = manager_cls

    @classmethod
    def update(
        cls, manager_type: str | DatabaseManagerType, manager_cls: type[DatabaseManagerInterface]
    ) -> None:
        normalized_key: str = cls._normalize_manager_type(manager_type)
        if normalized_key not in cls._FACTORY_REGISTRY:
            raise ValueError("Manager with provided key not found in factory registry!")
        cls._FACTORY_REGISTRY[normalized_key] = manager_cls

    @classmethod
    def get_manager_class(
        cls, manager_type: str | DatabaseManagerType
    ) -> type[DatabaseManagerInterface]:
        normalized_type: str = cls._normalize_manager_type(manager_type)
        manager_cls = cls._FACTORY_REGISTRY.get(normalized_type)

        if manager_cls is None:
            supported_types = ", ".join(sorted(cls._FACTORY_REGISTRY))
            raise ValueError(
                f"Unsupported database manager type: {manager_type}. "
                f"Supported types: {supported_types}."
            )

        return manager_cls

    @classmethod
    def create(
        cls, manager_type: str | DatabaseManagerType, *args: Any, **kwargs: Any
    ) -> DatabaseManagerInterface:
        manager_cls: type[DatabaseManagerInterface] = cls.get_manager_class(manager_type)
        return manager_cls(*args, **kwargs)

    @classmethod
    def create_from_env(
        cls, manager_type: str | DatabaseManagerType, *args: Any, **kwargs: Any
    ) -> DatabaseManagerInterface:
        manager_cls: type[DatabaseManagerInterface] = cls.get_manager_class(manager_type)
        return manager_cls.create_from_env(*args, **kwargs)


def create_manager(
    manager_type: str | DatabaseManagerType, *args: Any, **kwargs: Any
) -> DatabaseManagerInterface:
    return DatabaseManagerFactory.create(manager_type, *args, **kwargs)


def create_manager_from_env(
    manager_type: str | DatabaseManagerType, *args: Any, **kwargs: Any
) -> DatabaseManagerInterface:
    return DatabaseManagerFactory.create_from_env(manager_type, *args, **kwargs)


DatabaseManagerFactory.register("postgresql", PostgreSQLDatabaseManager)