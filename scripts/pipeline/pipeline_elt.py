"""Coordinate an ELT pipeline across configured sources, sinks, and load steps.

PipelineELT clears each staging table once, loads extracted source rows into
their configured staging destinations, then asks each sink to run its
transformations.
"""

from warnings import warn
from dataclasses import dataclass

from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.pipeline_callback_manager import (
    PipelineELTCallbackManager,
    PipelineEvent,
)
from scripts.pipeline.sink import Sink
from scripts.pipeline.source import Row, Source


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
class PipelineExtractResult:
    """Summary of source extraction.

    Attributes:
        sources_found: Number of load steps whose configured source exists.
        sources_not_found: Number of load steps skipped because the source was
            not configured.
        extracted_data: Extracted rows grouped by destination sink name.
    """

    sources_found: int
    sources_not_found: int
    extracted_data: dict[str, list[Row]]


@dataclass(frozen=True)
class PipelineClearResult:
    """Summary of staging table cleanup.

    Attributes:
        cleared_tables: Unique ``(sink_name, staging_table)`` pairs cleared
            successfully.
        uncleared_tables: Unique ``(sink_name, staging_table)`` pairs that
            could not be cleared.
    """

    cleared_tables: set[tuple[str, str]]
    uncleared_tables: set[tuple[str, str]]


@dataclass(frozen=True)
class PipelineLoadResult:
    """Summary of staging table loads.

    Attributes:
        loaded_steps: Names or identifiers of load steps that loaded
            successfully.
        failed_steps: Load-stage errors recorded while writing staging rows.
    """

    loaded_steps: list[str]
    failed_steps: list[PipelineStageError]


@dataclass(frozen=True)
class PipelineTransformationResult:
    """Summary of sink transformations.

    Attributes:
        transformed_sinks: Sink names whose transformations completed
            successfully.
        failed_steps: Transformation-stage errors recorded while running sink
            transformations.
    """

    transformed_sinks: list[str]
    failed_steps: list[PipelineStageError]


class PipelineELT:
    def __init__(
        self,
        sources: list[Source],
        sinks: list[Sink],
        load_steps: list[LoadStep],
        callback_manager: PipelineELTCallbackManager | None = None,
    ) -> None:
        self.sources: dict[str, Source] = {source.name: source for source in sources}
        self.sinks: dict[str, Sink] = {sink.name: sink for sink in sinks}
        self.load_steps: list[LoadStep] = load_steps
        self.callback_manager: PipelineELTCallbackManager = (
            callback_manager or PipelineELTCallbackManager()
        )

    def run(self) -> PipelineResult:
        """Run the full ELT pipeline and return a summary.

        The pipeline clears configured staging tables, extracts source rows,
        loads those rows into staging, then runs sink transformations.

        Returns:
            PipelineResult: Aggregated status for the full run, including
            cleared and uncleared staging tables, successfully loaded steps,
            and load/transformation failures.
        """
        clear_result: PipelineClearResult = self.clear_staging()
        extract_result: PipelineExtractResult = self.extract_from_sources()
        load_result: PipelineLoadResult = self.load_staging(
            extract_result.extracted_data
        )
        transformation_result: PipelineTransformationResult = self.run_transformations()

        failed_steps: list[PipelineStageError] = (
            load_result.failed_steps + transformation_result.failed_steps
        )

        return PipelineResult(
            is_success=(
                len(clear_result.uncleared_tables) == 0
                and extract_result.sources_not_found == 0
                and len(failed_steps) == 0
            ),
            cleared_tables=clear_result.cleared_tables,
            uncleared_tables=clear_result.uncleared_tables,
            loaded_steps=load_result.loaded_steps,
            failed_steps=failed_steps,
        )

    @staticmethod
    def _step_name(step: LoadStep) -> str:
        return (
            f"{step.source_name}:{step.source_resource}->"
            f"{step.sink_name}:{step.staging_table}"
        )

    def extract_from_sources(self) -> PipelineExtractResult:
        """Extract rows from sources referenced by load steps.

        Rows are grouped by destination sink name so extraction can be tested
        separately from staging writes. Missing sources and failed extractions
        are skipped with a ``RuntimeWarning``. Returns an empty dictionary when
        no rows could be extracted.
        """
        extracted_rows: dict[str, list[Row]] = {}
        sources_found: int = 0
        sources_not_found: int = 0
        sources = self.sources

        for step in self.load_steps:
            source: Source | None = sources.get(step.source_name)
            if source is None:
                sources_not_found += 1
                message: str = (
                    f"Source {step.source_name!r} was not found; skipping extract "
                    f"for resource {step.source_resource!r}."
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_extracting_stage_failure_callbacks(
                    PipelineEvent(
                        stage="extract",
                        is_success=False,
                        message=message,
                        step=step,
                        source_name=step.source_name,
                        source_resource=step.source_resource,
                        sink_name=step.sink_name,
                        staging_table=step.staging_table,
                    )
                )
                continue
            sources_found += 1

            try:
                rows: list[Row] = source.extract(step.source_resource)
            except Exception as exc:
                message = (
                    f"Failed to extract resource {step.source_resource!r} "
                    f"from source {step.source_name!r}: {exc}"
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_extracting_stage_failure_callbacks(
                    PipelineEvent(
                        stage="extract",
                        is_success=False,
                        message=message,
                        step=step,
                        source_name=step.source_name,
                        source_resource=step.source_resource,
                        sink_name=step.sink_name,
                        staging_table=step.staging_table,
                        exception=exc,
                    )
                )
                continue

            extracted_rows.setdefault(step.sink_name, []).extend(rows)
            self.callback_manager.run_extracting_stage_callbacks(
                PipelineEvent(
                    stage="extract",
                    is_success=True,
                    message=(
                        f"Extracted {len(rows)} rows from resource "
                        f"{step.source_resource!r}."
                    ),
                    step=step,
                    source_name=step.source_name,
                    source_resource=step.source_resource,
                    sink_name=step.sink_name,
                    staging_table=step.staging_table,
                    rows=rows,
                    row_count=len(rows),
                )
            )

        return PipelineExtractResult(
            sources_found=sources_found,
            sources_not_found=sources_not_found,
            extracted_data=extracted_rows,
        )

    def clear_staging(self) -> PipelineClearResult:
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
            packed_data: tuple[str, str] = (step.sink_name, step.staging_table)
            if packed_data in cleared_tables:
                continue

            sink: Sink | None = self.sinks.get(step.sink_name, None)
            if sink is None:
                uncleared_tables.add(packed_data)
                message = (
                    f"Sink {step.sink_name!r} was not found; skipping staging clear "
                    f"for table {step.staging_table!r}."
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_clearing_stage_failure_callbacks(
                    PipelineEvent(
                        stage="clear",
                        is_success=False,
                        message=message,
                        step=step,
                        source_name=step.source_name,
                        source_resource=step.source_resource,
                        sink_name=step.sink_name,
                        staging_table=step.staging_table,
                    )
                )
                continue
            try:
                sink.clear_staging(step.staging_table)
            except Exception as exc:
                uncleared_tables.add(packed_data)
                message = (
                    f"Failed to clear staging table {step.staging_table!r} "
                    f"for sink {step.sink_name!r}: {exc}"
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_clearing_stage_failure_callbacks(
                    PipelineEvent(
                        stage="clear",
                        is_success=False,
                        message=message,
                        step=step,
                        source_name=step.source_name,
                        source_resource=step.source_resource,
                        sink_name=step.sink_name,
                        staging_table=step.staging_table,
                        exception=exc,
                    )
                )
                continue
            cleared_tables.add(packed_data)
            self.callback_manager.run_clearing_stage_callbacks(
                PipelineEvent(
                    stage="clear",
                    is_success=True,
                    message=(
                        f"Cleared staging table {step.staging_table!r} "
                        f"for sink {step.sink_name!r}."
                    ),
                    step=step,
                    source_name=step.source_name,
                    source_resource=step.source_resource,
                    sink_name=step.sink_name,
                    staging_table=step.staging_table,
                )
            )

        return PipelineClearResult(
            cleared_tables=cleared_tables,
            uncleared_tables=uncleared_tables,
        )

    def load_staging(self, extracted_rows: dict[str, list[Row]]) -> PipelineLoadResult:
        """Load extracted rows into staging tables referenced by load steps.

        ``extracted_rows`` is a descriptor keyed by sink name, usually returned
        by :meth:`extract_from_sources`. Missing sinks, missing extracted rows,
        and failed loads are skipped with a ``RuntimeWarning``.
        """
        loaded_steps: list[str] = []
        failed_steps: list[PipelineStageError] = []

        for step in self.load_steps:
            sink: Sink | None = self.sinks.get(step.sink_name)
            if sink is None:
                message = (
                    f"Sink {step.sink_name!r} was not found; skipping staging load "
                    f"for table {step.staging_table!r}."
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_loading_stage_failure_callbacks(
                    PipelineEvent(
                        stage="load",
                        is_success=False,
                        message=message,
                        step=step,
                        source_name=step.source_name,
                        source_resource=step.source_resource,
                        sink_name=step.sink_name,
                        staging_table=step.staging_table,
                    )
                )
                failed_steps.append(
                    PipelineStageError(
                        stage="load",
                        step_name=self._step_name(step),
                        message=message,
                        exception=None,
                    )
                )
                continue

            rows: list[Row] | None = extracted_rows.get(step.sink_name)
            if rows is None:
                message: str = (
                    f"No extracted rows found for sink {step.sink_name!r}; skipping "
                    f"staging load for table {step.staging_table!r}."
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_loading_stage_failure_callbacks(
                    PipelineEvent(
                        stage="load",
                        is_success=False,
                        message=message,
                        step=step,
                        source_name=step.source_name,
                        source_resource=step.source_resource,
                        sink_name=step.sink_name,
                        staging_table=step.staging_table,
                    )
                )
                failed_steps.append(
                    PipelineStageError(
                        stage="load",
                        step_name=self._step_name(step),
                        message=message,
                        exception=None,
                    )
                )
                continue

            try:
                loaded_count: int = sink.load_staging(step.staging_table, rows)
            except Exception as exc:
                message: str = (
                    f"Failed to load staging table {step.staging_table!r} "
                    f"for sink {step.sink_name!r}: {exc}"
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_loading_stage_failure_callbacks(
                    PipelineEvent(
                        stage="load",
                        is_success=False,
                        message=message,
                        step=step,
                        source_name=step.source_name,
                        source_resource=step.source_resource,
                        sink_name=step.sink_name,
                        staging_table=step.staging_table,
                        rows=rows,
                        row_count=len(rows),
                        exception=exc,
                    )
                )
                failed_steps.append(
                    PipelineStageError(
                        stage="load",
                        step_name=self._step_name(step),
                        message=message,
                        exception=exc,
                    )
                )
                continue
            loaded_steps.append(self._step_name(step))
            self.callback_manager.run_loading_stage_callbacks(
                PipelineEvent(
                    stage="load",
                    is_success=True,
                    message=(
                        f"Loaded {loaded_count} rows into staging table "
                        f"{step.staging_table!r} for sink {step.sink_name!r}."
                    ),
                    step=step,
                    source_name=step.source_name,
                    source_resource=step.source_resource,
                    sink_name=step.sink_name,
                    staging_table=step.staging_table,
                    rows=rows,
                    row_count=len(rows),
                    loaded_count=loaded_count,
                )
            )

        return PipelineLoadResult(
            loaded_steps=loaded_steps,
            failed_steps=failed_steps,
        )

    def run_transformations(self) -> PipelineTransformationResult:
        """Run transformation steps for every configured sink.

        Each configured sink is asked to run its transformations once. Failed
        transformations are skipped.
        """
        transformed_sinks: list[str] = []
        failed_steps: list[PipelineStageError] = []

        for sink in self.sinks.values():
            try:
                sink.run_transformations()
            except Exception as exc:
                message: str = (
                    f"Failed to run transformations for sink {sink.name!r}: {exc}"
                )
                warn(
                    message,
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.callback_manager.run_transformation_stage_failure_callbacks(
                    PipelineEvent(
                        stage="transform",
                        is_success=False,
                        message=message,
                        sink_name=sink.name,
                        exception=exc,
                    )
                )
                failed_steps.append(
                    PipelineStageError(
                        stage="transform",
                        step_name=sink.name,
                        message=message,
                        exception=exc,
                    )
                )
                continue
            transformed_sinks.append(sink.name)
            self.callback_manager.run_transformation_stage_callbacks(
                PipelineEvent(
                    stage="transform",
                    is_success=True,
                    message=f"Ran transformations for sink {sink.name!r}.",
                    sink_name=sink.name,
                )
            )

        return PipelineTransformationResult(
            transformed_sinks=transformed_sinks,
            failed_steps=failed_steps,
        )
