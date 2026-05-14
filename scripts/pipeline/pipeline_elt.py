from source import Source
from sink import Sink
from load_step import LoadStep


class PipelineELT:
    def __init__(
        self,
        sources: list[Source],
        sinks: list[Sink],
        load_steps: list[LoadStep]
    ) -> None:
        self.sources = {source.name: source for source in sources}
        self.sinks = {sink.name: sink for sink in sinks}
        self.load_steps = load_steps

    def run(self) -> None:
        self.clear_staging()
        self.load_staging()
        self.run_transformations()

    def clear_staging(self) -> None:
        cleared_tables = set()

        for step in self.load_steps:

            if (step.sink_name, step.staging_table) in cleared_tables:
                continue

            sink = self.sinks[step.sink_name]
            sink.clear_staging(step.staging_table)
            cleared_tables.add(step.sink_name, step.staging_table)

    def load_staging(self) -> None:
        for step in self.load_steps:
            source = self.sources[step.source_name]
            sink = self.sinks[step.sink_name]

            rows = source.extract(step.source_resource)
            sink.load_staging(step.staging_table, rows)

    def run_transformations(self) -> None:
        for sink in self.sinks.values():
            sink.run_transformations()
