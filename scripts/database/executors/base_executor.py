from __future__ import annotations

from abc import ABC, abstractmethod
from psycopg.cursor import Cursor
from typing import Generic, TypeVar, Any, Callable

QueryT = TypeVar("QueryT")
ParamsT = TypeVar("ParamsT")


class BaseExecutor(ABC, Generic[QueryT, ParamsT]):

    @abstractmethod
    def execute(
        self,
        query: QueryT,
        params: ParamsT,
        cursor_callback: Callable[[Cursor], Any],
        **exec_kwargs: dict[str, Any],
    ) -> None:
        """Execute a query with optional parameters and backend-specific options."""
        pass
