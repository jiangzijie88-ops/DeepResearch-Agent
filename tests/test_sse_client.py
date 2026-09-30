import json

import pytest

from frontend.streaming import iter_workflow_events


def test_parser_yields_before_requesting_later_frames():
    consumed = []
    def lines():
        yield ": heartbeat"
        yield ""
        yield "event: stage_started"
        yield 'data: {"type":"stage_started","message":"正在生成研究计划"}'
        yield ""
        consumed.append("later")
        yield 'data: {"type":"workflow_completed"}'
        yield ""
    events = iter_workflow_events(lines())
    assert next(events)["message"] == "正在生成研究计划"
    assert consumed == []
    assert next(events)["type"] == "workflow_completed"


@pytest.mark.parametrize("lines", [["not sse"], ['data: {"type":"progress"}'], ["data: nope", ""]])
def test_parser_rejects_invalid_or_truncated_stream(lines):
    with pytest.raises(ValueError):
        list(iter_workflow_events(lines))
