from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, Protocol, TypeVar, runtime_checkable

from scripts.database.models.database_types import DatabaseOperationResult
from scripts.database.models.query import Query


@runtime_checkable
class DatabaseManagerLoggerInterface(Protocol):
    """Interface for manager-level database operation logging."""

    def connect_started(self, manager_name: str) -> None: ...

    def connect_succeeded(self, manager_name: str) -> None: ...

    def connect_failed(self, manager_name: str, error: Exception) -> None: ...

    def close_started(self, manager_name: str) -> None: ...

    def close_succeeded(self, manager_name: str) -> None: ...

    def close_failed(self, manager_name: str, error: Exception) -> None: ...

    def push_started(self, manager_name: str, table_name: str, rows_count: int) -> None: ...

    def push_succeeded(
        self, manager_name: str, table_name: str, result: DatabaseOperationResult
    ) -> None: ...

    def push_failed(self, manager_name: str, table_name: str, error: Exception) -> None: ...

    def fetch_started(self, manager_name: str, query: Query | str) -> None: ...

    def fetch_succeeded(self, manager_name: str, result: DatabaseOperationResult) -> None: ...

    def fetch_failed(self, manager_name: str, query: Query | str, error: Exception) -> None: ...

    def execute_started(self, manager_name: str, query: Query | str) -> None: ...

    def execute_succeeded(self, manager_name: str, query: Query | str) -> None: ...

    def execute_failed(self, manager_name: str, query: Query | str, error: Exception) -> None: ...


class DatabaseManagerLoggingTarget(Protocol):
    manager_name: str
    database_logger: DatabaseManagerLoggerInterface | None


P = ParamSpec("P")
R = TypeVar("R")


def log_database_lifecycle(
    *,
    started: str,
    succeeded: str,
    failed: str,
) -> Callable[
    [Callable[Concatenate[DatabaseManagerLoggingTarget, P], R]],
    Callable[Concatenate[DatabaseManagerLoggingTarget, P], R],
]:
    """Log manager lifecycle methods without pushing logging into components."""

    def decorator(
        method: Callable[Concatenate[DatabaseManagerLoggingTarget, P], R],
    ) -> Callable[Concatenate[DatabaseManagerLoggingTarget, P], R]:
        @wraps(method)
        def wrapper(
            self: DatabaseManagerLoggingTarget,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            if self.database_logger is not None:
                getattr(self.database_logger, started)(self.manager_name)

            try:
                result = method(self, *args, **kwargs)
            except Exception as exc:
                if self.database_logger is not None:
                    getattr(self.database_logger, failed)(self.manager_name, exc)
                raise

            if self.database_logger is not None:
                getattr(self.database_logger, succeeded)(self.manager_name)
            return result

        return wrapper

    return decorator
