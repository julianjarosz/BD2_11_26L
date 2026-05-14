from dataclasses import dataclass


@dataclass(frozen=True)
class LoadStep:
    source_name: str  # from where do we take?
    source_resource: str  # what do we take?
    sink_name: str  # to where we take?
    staging_table: str  # where do we stage?
