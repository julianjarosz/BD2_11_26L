from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Generic, TypeVar, Any

QueryT = TypeVar("QueryT")
ParamsT = TypeVar("ParamsT")


class BaseExecutor(ABC, Generic[QueryT, ParamsT]):

    @abstractmethod
    def execute(self, query: QueryT, params: ParamsT, **exec_kwargs: dict[str, Any]) -> None:
        """Execute a query with optional parameters and backend-specific options."""
        pass
