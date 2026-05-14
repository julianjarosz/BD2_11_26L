"""Coordinate an ELT pipeline across configured sources, sinks, and load steps.

PipelineELT clears each staging table once, loads extracted source rows into
their configured staging destinations, then asks each sink to run its
transformations.
"""

import warnings

from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.sink import Sink
from scripts.pipeline.source import Source


class PipelineELT:
    def __init__(
        self, sources: list[Source], sinks: list[Sink], load_steps: list[LoadStep]
    ) -> None:
        self.sources: dict[str, Source] = {source.name: source for source in sources}
        self.sinks: dict[str, Sink] = {sink.name: sink for sink in sinks}
        self.load_steps: list[LoadStep] = load_steps

    def run(self) -> None:
        self.clear_staging()
        self.load_staging()
        self.run_transformations()

    def clear_staging(self) -> set[tuple[str, str]] | None:
        """Clear staging tables referenced by load steps.

        Each unique ``(sink_name, staging_table)`` pair is cleared at most once,
        even if multiple load steps target the same table. Missing sinks and
        failed clears are skipped with a ``RuntimeWarning`` and returned as a set
        of uncleared ``(sink_name, staging_table)`` pairs. Returns ``None`` when
        every referenced staging table was cleared successfully.
        """
        cleared_tables: set[tuple[str, str]] = set()
        uncleared_tables: set[tuple[str, str]] = set()

        for step in self.load_steps:

            if (step.sink_name, step.staging_table) in cleared_tables:
                continue

            sink: Sink | None = self.sinks.get(step.sink_name, None)
            if sink is None:
                uncleared_tables.add((step.sink_name, step.staging_table))
                warnings.warn(
                    f"Sink {step.sink_name!r} was not found; skipping staging clear "
                    f"for table {step.staging_table!r}.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            try:
                sink.clear_staging(step.staging_table)
            except Exception as exc:
                uncleared_tables.add((step.sink_name, step.staging_table))
                warnings.warn(
                    f"Failed to clear staging table {step.staging_table!r} "
                    f"for sink {step.sink_name!r}: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            cleared_tables.add((step.sink_name, step.staging_table))
            
        return uncleared_tables if len(uncleared_tables) != 0 else None

    def load_staging(self) -> None:
        for step in self.load_steps:
            source = self.sources[step.source_name]
            sink = self.sinks[step.sink_name]

            rows = source.extract(step.source_resource)
            sink.load_staging(step.staging_table, rows)

    def run_transformations(self) -> None:
        for sink in self.sinks.values():
            sink.run_transformations()
