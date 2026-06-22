from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from warnings import warn

from scripts.pipeline.load_step import LoadStep
from scripts.pipeline.source import Row


@dataclass(frozen=True)
class PipelineEvent:
    """Event passed to pipeline callbacks.

    Attributes:
        stage: Pipeline stage that emitted the event, such as ``"extract"``,
            ``"clear"``, ``"load"``, or ``"transform"``.
        is_success: ``True`` for successful stage events, ``False`` for failed
            or skipped stage events.
        message: Human-readable summary of the event.
        step: Load step associated with the event, or ``None`` when the event is
            not tied to a single load step.
        source_name: Source name associated with the event, when available.
        source_resource: Source resource associated with the event, when
            available.
        sink_name: Sink name associated with the event, when available.
        staging_table: Staging table associated with the event, when available.
        rows: Rows handled by the stage, when the event includes row data.
        row_count: Number of rows handled by the stage, when known.
        loaded_count: Number of rows reported as loaded by the sink, when known.
        exception: Exception raised by the stage, or ``None`` for successful
            events and non-exception skips.
        context: Optional extra event metadata for stage-specific details.
    """

    stage: str
    is_success: bool
    message: str
    step: LoadStep | None = None
    source_name: str | None = None
    source_resource: str | None = None
    sink_name: str | None = None
    staging_table: str | None = None
    rows: list[Row] | None = None
    row_count: int | None = None
    loaded_count: int | None = None
    exception: Exception | None = None
    context: dict[str, Any] | None = None


PipelineCallback = Callable[[PipelineEvent], None]
"""Callable type for pipeline callbacks."""


class PipelineELTCallbackManager:
    """Store and run callbacks for ELT pipeline stage events.

    Each stage has one callback list for successful events and one callback
    list for failed or skipped events. Callback exceptions are converted into
    ``RuntimeWarning`` messages so one callback cannot stop the pipeline.
    """

    def __init__(self) -> None:
        """Create an empty callback manager."""
        self.extracting_stage_callbacks: list[PipelineCallback] = []
        self.extracting_stage_failure_callbacks: list[PipelineCallback] = []
        self.clearing_stage_callbacks: list[PipelineCallback] = []
        self.clearing_stage_failure_callbacks: list[PipelineCallback] = []
        self.loading_stage_callbacks: list[PipelineCallback] = []
        self.loading_stage_failure_callbacks: list[PipelineCallback] = []
        self.transformation_stage_callbacks: list[PipelineCallback] = []
        self.transformation_stage_failure_callbacks: list[PipelineCallback] = []

    def run_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks that match the event stage and success state."""
        self._run_callbacks(self._callbacks_for(event), event)

    def run_extracting_stage_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for successful extraction events."""
        self._run_callbacks(self.extracting_stage_callbacks, event)

    def run_extracting_stage_failure_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for failed or skipped extraction events."""
        self._run_callbacks(self.extracting_stage_failure_callbacks, event)

    def run_clearing_stage_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for successful staging clear events."""
        self._run_callbacks(self.clearing_stage_callbacks, event)

    def run_clearing_stage_failure_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for failed or skipped staging clear events."""
        self._run_callbacks(self.clearing_stage_failure_callbacks, event)

    def run_loading_stage_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for successful staging load events."""
        self._run_callbacks(self.loading_stage_callbacks, event)

    def run_loading_stage_failure_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for failed or skipped staging load events."""
        self._run_callbacks(self.loading_stage_failure_callbacks, event)

    def run_transformation_stage_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for successful transformation events."""
        self._run_callbacks(self.transformation_stage_callbacks, event)

    def run_transformation_stage_failure_callbacks(self, event: PipelineEvent) -> None:
        """Run callbacks registered for failed transformation events."""
        self._run_callbacks(self.transformation_stage_failure_callbacks, event)

    def _callbacks_for(self, event: PipelineEvent) -> list[PipelineCallback]:
        """Return the callback list matching the event stage and status."""
        callbacks_by_stage = {
            ("extract", True): self.extracting_stage_callbacks,
            ("extract", False): self.extracting_stage_failure_callbacks,
            ("clear", True): self.clearing_stage_callbacks,
            ("clear", False): self.clearing_stage_failure_callbacks,
            ("load", True): self.loading_stage_callbacks,
            ("load", False): self.loading_stage_failure_callbacks,
            ("transform", True): self.transformation_stage_callbacks,
            ("transform", False): self.transformation_stage_failure_callbacks,
        }
        return callbacks_by_stage.get((event.stage, event.is_success), [])

    def _run_callbacks(self, callbacks: list[PipelineCallback], event: PipelineEvent) -> None:
        """Run callbacks for one event and warn about callback failures."""
        for callback in callbacks:
            try:
                callback(event)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                callback_name = getattr(callback, "__name__", callback.__class__.__name__)
                warn(
                    f"Pipeline callback {callback_name!r} failed during "
                    f"{event.stage!r} stage: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
