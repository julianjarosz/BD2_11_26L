from __future__ import annotations

import abc
import typing

from scripts.database.models.database_types import DatabaseRow, DatabaseOperationResult
from scripts.database.executors.base_executor import BaseExecutor
from scripts.database.builders.base_query_builder import BaseQueryBuilder


class BasePusher(abc.ABC):
    """
    Base interface for database pushers.

    A pusher owns a query executor and query-builder type, then exposes insert
    operations that return per-row success and failure metadata.
    """
    
    def __init__(self, 
                 query_executor: BaseExecutor[typing.Any, typing.Any],
                 builder_t: type[BaseQueryBuilder]
                 ) -> None:
        
        self.query_executor: BaseExecutor[typing.Any, typing.Any] = query_executor
        self.builder_t: type[BaseQueryBuilder] = builder_t
        
    
    @abc.abstractmethod
    def insert(self, table_name: str, rows: list[DatabaseRow]) -> DatabaseOperationResult:
        """
        Insert rows into table_name and return operation metadata.

        Implementations should report successfully inserted rows and rows that
        failed during insertion in the returned DatabaseOperationResult.
        """
        pass
