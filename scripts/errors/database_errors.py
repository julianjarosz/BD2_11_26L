"""Custom exceptions raised by database managers."""


class NormalizingRowsException(ValueError):
    """Exception raised when rows cannot be normalized for database operations."""

    def __init__(self, error_msg: str) -> None:
        super().__init__(error_msg)


class EmptyRowException(ValueError):
    """Exception raised when a database row has no columns."""

    def __init__(self, error_msg: str, *, row: object | None = None) -> None:
        super().__init__(error_msg)
        self.row = row


class InvalidTableException(ValueError):
    """Exception raised when a database table name is invalid."""

    def __init__(self, error_msg: str, *, table: object | None = None) -> None:
        super().__init__(error_msg)
        self.table = table


class EmptyPayloadException(ValueError):
    """Exception raised when a database payload has no rows."""

    def __init__(self, error_msg: str, *, payload: object | None = None) -> None:
        super().__init__(error_msg)
        self.payload = payload


class InvalidRequestType(ValueError):
    """Exception raised when a database request type is not supported."""

    def __init__(self, error_msg: str, *, request_type: object | None = None) -> None:
        super().__init__(error_msg)
        self.request_type = request_type


class DatabaseConnectionException(ConnectionError):
    """Exception raised when a database connection cannot be established."""

    def __init__(
        self,
        error_msg: str,
        *,
        database_name: str | None = None,
        host: str | None = None,
        port: int | None = None,
        env_var: str | None = None,
    ) -> None:
        super().__init__(error_msg)
        self.database_name = database_name
        self.host = host
        self.port = port
        self.env_var = env_var
