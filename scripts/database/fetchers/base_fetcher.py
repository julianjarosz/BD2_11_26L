from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any

from scripts.database.models.database_types import DatabaseOperationResult

QueryT = TypeVar("QueryT")
ParamsT = TypeVar("ParamsT")


class BaseFetcher(ABC, Generic[QueryT, ParamsT]):
    @abstractmethod
    def fetch(
        self, query: QueryT, params: ParamsT, **exec_kwargs: dict[str, Any]
    ) -> DatabaseOperationResult:
        """Fetch data for a query and return operation metadata."""
        pass
