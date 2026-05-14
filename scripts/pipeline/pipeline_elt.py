"""Coordinate an ELT pipeline across configured sources, sinks, and load steps.

PipelineELT clears each staging table once, loads extracted source rows into
their configured staging destinations, then asks each sink to run its
transformations.
"""

from warnings import warn
from dataclasses import dataclass
from typing import Callable

from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.sink import Sink
from scripts.pipeline.source import Source


@dataclass(frozen=True)
class PipelineStageError:
    """Failure captured while executing one stage of the ELT pipeline.

    Attributes:
        stage: Pipeline phase that produced the failure, such as ``"clear"``,
            ``"load"``, or ``"transform"``.
        step_name: Load step, sink, or transformation identifier associated
            with the failure, or ``None`` when the error is not tied to a
            single configured step.
        message: Human-readable summary suitable for logs, warnings, or result
            reporting.
        exception: Original exception raised by the stage, or ``None`` when the
            failure was recorded without an exception object.
    """

    stage: str
    step_name: str | None
    message: str
    exception: Exception | None


@dataclass(frozen=True)
class PipelineResult:
    """Summary of a single ELT pipeline run.

    Attributes:
        is_success: ``True`` when staging clears, loads, and transformations
            completed without recorded failures.
        cleared_tables: Unique ``(sink_name, staging_table)`` pairs cleared
            before loading.
        uncleared_tables: Unique ``(sink_name, staging_table)`` pairs that
            could not be cleared.
        loaded_steps: Names or identifiers of load steps that completed
            successfully.
        failed_steps: Pipeline errors recorded while clearing, loading, or
            transforming data.
    """

    is_success: bool
    cleared_tables: set[tuple[str, str]]
    uncleared_tables: set[tuple[str, str]]
    loaded_steps: list[str]
    failed_steps: list[PipelineStageError]


@dataclass(frozen=True)
class PipelineEvent: ...


ELTCallback = Callable[[PipelineEvent], None]


class PipelineELT:
    def __init__(
        self, sources: list[Source], sinks: list[Sink], load_steps: list[LoadStep]
    ) -> None:
        self.sources: dict[str, Source] = {source.name: source for source in sources}
        self.sinks: dict[str, Sink] = {sink.name: sink for sink in sinks}
        self.load_steps: list[LoadStep] = load_steps

        self.clearing_stage_callbacks: list[ELTCallback] = []
        self.loading_stage_callbacks: list[ELTCallback] = []
        self.transformation_stage_callbacks: list[ELTCallback] = []

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
                warn(
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
                warn(
                    f"Failed to clear staging table {step.staging_table!r} "
                    f"for sink {step.sink_name!r}: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            packed_data: tuple[str, str] = (step.sink_name, step.staging_table)
            cleared_tables.add(packed_data)

            for callback in self.clearing_stage_callbacks:
                try:
                    callback(packed_data)
                except Exception as exc:
                    callback_name: str = getattr(
                        callback, "__name__", callback.__class__.__name__
                    )
                    warn(
                        f"Clearing stage callback {callback_name!r} failed for "
                        f"{packed_data!r}: {exc}",
                        RuntimeWarning,
                        stacklevel=2,
                    )

        return uncleared_tables if len(uncleared_tables) != 0 else None

    def load_staging(self) -> None:
        for step in self.load_steps:
            source: Source | None = self.sources.get(step.source_name, None)
            if source is None:
                # TODO: implement warn and add failure step on source
                ...
            sink: Sink | None = self.sinks.get(step.sink_name, None)
            if sink is None:
                # TODO: implement warn and add failure step on sink
                ...

            try:
                rows: list = source.extract(step.source_resource)
            except Exception:
                # TODO - warn and extracing logging
                ...
            sink.load_staging(step.staging_table, rows)

    def run_transformations(self) -> None:
        for sink in self.sinks.values():
            sink.run_transformations()
