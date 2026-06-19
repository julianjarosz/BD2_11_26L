from scripts.database.managers.base import (
    DatabaseManagerInterface,
    DatabasePayloadPreparer,
    DatabasePayloadNormalizer,
    PayloadNormalizerInterface,
    PayloadSchemaValidatorInterface,
    PreparedDatabasePayload,
    RejectedDatabaseRow,
    TableSchemaRowValidator,
)
from scripts.database.managers.factory import (
    DatabaseManagerFactory,
    DatabaseManagerType,
    create_manager,
    create_manager_from_env,
)

_POSTGRESQL_EXPORTS = {
    "POSTGRES_DSN_ENV_VAR",
    "PostgreSQLDatabaseConnector",
    "PostgreSQLDatabaseManager",
    "PostgreSQLDatabaseManagerContext",
}

__all__ = [
    "POSTGRES_DSN_ENV_VAR",
    "DatabaseManagerFactory",
    "DatabaseManagerInterface",
    "DatabaseManagerType",
    "DatabasePayloadPreparer",
    "DatabasePayloadNormalizer",
    "PayloadNormalizerInterface",
    "PayloadSchemaValidatorInterface",
    "PostgreSQLDatabaseConnector",
    "PostgreSQLDatabaseManager",
    "PostgreSQLDatabaseManagerContext",
    "PreparedDatabasePayload",
    "RejectedDatabaseRow",
    "TableSchemaRowValidator",
    "create_manager",
    "create_manager_from_env",
]


def __getattr__(name: str):
    if name not in _POSTGRESQL_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from scripts.database.managers import postgresql

    value = getattr(postgresql, name)
    globals()[name] = value
    return value
