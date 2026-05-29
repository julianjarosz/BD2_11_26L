from dataclasses import dataclass

try:
    from source import Source
    from sink import Sink
except ModuleNotFoundError:
    from scripts.pipeline.sink import Sink
    from scripts.pipeline.source import Source


@dataclass(frozen=True)
class LoadStep:
    source: Source  # from where do we take?
    source_resource: str  # what do we take?
    sink: Sink  # to where we take?
    staging_table: str  # where do we stage?
