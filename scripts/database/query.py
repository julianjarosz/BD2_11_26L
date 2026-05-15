from __future__ import annotations

from typing import Any


class Query:
    """Query object representing a SQL query with parameters."""

    def __init__(self, query: str, *args: tuple, **kwargs: dict[str, Any]) -> None:
        """
        Initialize the Query object.

        Parameters:
            query: SQL query to execute.
            args: Arguments to pass to the query.
            kwargs: Keyword arguments to pass to the query.
        """
        self._query: str = query
        self._args: tuple = args
        self._kwargs: dict[str, Any] = kwargs

    @property
    def query_string(self) -> str:
        return self._query

    @property
    def formatted_query(self) -> str:
        return self._query.format(*self.args, **self.kwargs)
