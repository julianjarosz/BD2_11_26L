"""Database fetchers."""

from scripts.database.fetchers.base_fetcher import BaseFetcher
from scripts.database.fetchers.postgresql_fetcher import PostgreSQLDatabaseFetcher

__all__ = ["BaseFetcher", "PostgreSQLDatabaseFetcher"]
