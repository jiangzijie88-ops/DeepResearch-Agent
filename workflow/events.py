"""Optional runtime progress, independent of HTTP and persisted state."""

from functools import wraps
import logging
from typing import Callable, Literal

from pydantic import BaseModel, Field


class WorkflowEvent(BaseModel):
    type: Literal["workflow_started", "stage_started", "stage_completed", "progress",
                  "warning", "workflow_completed", "workflow_failed"]
    stage: str
    message: str
    data: dict = Field(default_factory=dict)


EventSink = Callable[[WorkflowEvent], None]


def emit_event(sink: EventSink | None, kind: str, stage: str, message: str, **data):
    if sink is not None:
        try:
            sink(WorkflowEvent(type=kind, stage=stage, message=message, data=data))
        except Exception:
            logging.getLogger(__name__).exception("Progress callback failed")


def completion_data(state) -> dict:
    return dict(question=state.question, status=state.status.value,
                report=state.final_report or state.draft_report or "No report generated.",
                evidence_count=len(state.evidence),
                evidence=[item.model_dump(mode="json") for item in state.evidence])


def workflow_lifecycle(function):
    """Add lifecycle events without changing synchronous return/exception behavior."""
    @wraps(function)
    def run(*args, **kwargs):
        sink = kwargs.get("on_event")
        emit_event(sink, "workflow_started", "workflow", "研究开始")
        try:
            state = function(*args, **kwargs)
        except Exception:
            emit_event(sink, "workflow_failed", "workflow", "研究过程中发生错误")
            raise
        if sink is not None:
            emit_event(sink, "workflow_completed", "final", "研究完成", **completion_data(state))
        return state
    return run
