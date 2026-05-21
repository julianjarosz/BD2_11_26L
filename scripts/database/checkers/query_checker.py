"""Interface for checking database queries before execution."""

from __future__ import annotations

import typing


class DatabaseQueryChecker(typing.Protocol):
    def safe_check_query(self, query: str) -> None:
        """Raise an exception when query is not allowed."""
