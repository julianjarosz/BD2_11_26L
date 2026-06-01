from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Callable

QueryT = TypeVar("QueryT")
ParamsT = TypeVar("ParamsT")


class BaseExecutor(ABC, Generic[QueryT, ParamsT]):

    @abstractmethod
    def execute(
        self,
        query: QueryT,
        params: ParamsT,
        callback: Callable[..., Any] | None = None,
        **exec_kwargs: dict[str, Any],
    ) -> Any:
        """Execute a query with optional parameters and backend-specific options."""
        pass
