"""Custom exceptions raised by database managers."""


class NormalizingRowsException(ValueError):
    """Exception raised when rows cannot be normalized for database operations."""

    def __init__(self, error_msg: str) -> None:
        super().__init__(error_msg)
