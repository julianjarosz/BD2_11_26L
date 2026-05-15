"""Database manager interface used by concrete database backends."""

from __future__ import annotations

import abc
import database_types as db_types
from query import Query
from typing import Any


class DatabaseManagerInterface(abc.ABC):
    """Interface for pushing data to and fetching data from a database."""

    @abc.abstractmethod
    def push_data(
        self,
        table_name: str,
        data: db_types.DatabasePayload,
        **push_op_kwargs: dict[str, Any],
    ) -> db_types.DatabaseOperationResult:
        """
        Push one or more rows into table_name.
        Parameters:
            table_name: Name of the table to push data to.
            data: DatabasePayload containing the data to push.

        Returns:
            DatabaseOperationResult containing metadata about the operation.
        """
        pass

    @abc.abstractmethod
    def fetch_data(
        self, query: Query | str, **fetch_op_kwargs: dict[str, Any]
    ) -> db_types.DatabaseOperationResult:
        """Fetch rows from the database using query or Query object and optional params.

        Parameters:
            query: SQL query or Query object to execute.
            fetch_op_kwargs: Optional keyword arguments for the fetch operation.

        Returns:
            DatabaseOperationResult containing metadata about the operation.
        """
        pass

    @abc.abstractmethod
    def execute(self, query: str | Query, **execute_op_kwargs: dict[str, Any]) -> None:
        """
        Executes SQL command that does not return anything using query or Query object and optional params.

        Parameters:
            query: SQL query or Query object to execute.
            execute_op_kwargs: Optional keyword arguments for the execute operation.
        """
        pass

    @abc.abstractmethod
    def close(self) -> None:
        """Close database resources held by the manager."""
        pass
