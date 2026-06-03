from __future__ import annotations

import logging

from scripts.database.models.database_types import DatabaseOperationResult
from scripts.database.models.query import Query


class PythonDatabaseManagerLogger:
    """Database manager logger backed by Python's logging module."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def connect_started(self, manager_name: str) -> None:
        self.logger.info("Opening %s database manager connection.", manager_name)

    def connect_succeeded(self, manager_name: str) -> None:
        self.logger.info("Opened %s database manager connection.", manager_name)

    def connect_failed(self, manager_name: str, error: Exception) -> None:
        self.logger.error(
            "Failed to open %s database manager connection: %s",
            manager_name,
            error,
        )

    def close_started(self, manager_name: str) -> None:
        self.logger.info("Closing %s database manager connection.", manager_name)

    def close_succeeded(self, manager_name: str) -> None:
        self.logger.info("Closed %s database manager connection.", manager_name)

    def close_failed(self, manager_name: str, error: Exception) -> None:
        self.logger.error(
            "Failed to close %s database manager connection: %s",
            manager_name,
            error,
        )

    def push_started(self, manager_name: str, table_name: str, rows_count: int) -> None:
        self.logger.info(
            "Starting %s push: table=%s rows=%s",
            manager_name,
            table_name,
            rows_count,
        )

    def push_succeeded(
        self, manager_name: str, table_name: str, result: DatabaseOperationResult
    ) -> None:
        self.logger.info(
            "Finished %s push: table=%s successful_rows=%s failed_rows=%s",
            manager_name,
            table_name,
            result.number_of_successful_rows,
            result.number_of_failed_rows,
        )

    def push_failed(self, manager_name: str, table_name: str, error: Exception) -> None:
        self.logger.error(
            "Failed %s push: table=%s error=%s",
            manager_name,
            table_name,
            error,
        )

    def fetch_started(self, manager_name: str, query: Query | str) -> None:
        self.logger.info("Starting %s fetch.", manager_name)

    def fetch_succeeded(self, manager_name: str, result: DatabaseOperationResult) -> None:
        self.logger.info(
            "Finished %s fetch: successful_rows=%s failed_rows=%s",
            manager_name,
            result.number_of_successful_rows,
            result.number_of_failed_rows,
        )

    def fetch_failed(self, manager_name: str, query: Query | str, error: Exception) -> None:
        self.logger.error(
            "Failed %s fetch: error=%s",
            manager_name,
            error,
        )

    def execute_started(self, manager_name: str, query: Query | str) -> None:
        self.logger.info("Starting %s execute.", manager_name)

    def execute_succeeded(self, manager_name: str, query: Query | str) -> None:
        self.logger.info("Finished %s execute.", manager_name)

    def execute_failed(self, manager_name: str, query: Query | str, error: Exception) -> None:
        self.logger.error(
            "Failed %s execute: error=%s",
            manager_name,
            error,
        )
