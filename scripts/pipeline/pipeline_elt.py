from __future__ import annotations

try:
    from load_step import LoadStep
except ModuleNotFoundError:
    from scripts.pipeline.load_step import LoadStep


class PipelineELT:
    def __init__(
        self,
        load_steps: list[LoadStep],
    ) -> None:
        self.load_steps = load_steps

    def run(self) -> None:
        cleared_tables = set()
        active_sink = None

        for step in self.load_steps:
            if active_sink is not None and step.sink is not active_sink:
                active_sink.run_transformations()

            active_sink = step.sink
            table_key = (id(step.sink), step.staging_table)

            if table_key not in cleared_tables:
                step.sink.clear_staging(step.staging_table)
                cleared_tables.add(table_key)

            self.load_step(step)

        if active_sink is not None:
            active_sink.run_transformations()

    def clear_staging(self) -> None:
        cleared_tables = set()

        for step in self.load_steps:
            table_key = (id(step.sink), step.staging_table)
            if table_key in cleared_tables:
                continue

            step.sink.clear_staging(step.staging_table)
            cleared_tables.add(table_key)

    def load_staging(self) -> None:
        for step in self.load_steps:
            self.load_step(step)

    def load_step(self, step: LoadStep) -> None:
        rows = step.source.extract(step.source_resource)
        step.sink.load_staging(step.staging_table, rows)

    def run_transformations(self) -> None:
        transformed_sinks = set()

        for step in self.load_steps:
            if id(step.sink) in transformed_sinks:
                continue

            step.sink.run_transformations()
            transformed_sinks.add(id(step.sink))
