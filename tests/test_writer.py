"""Verify Writer prompt composition and string output without network calls."""

from unittest.mock import Mock

import pytest
from langchain_openai import ChatOpenAI

from workers import writer
from workflow.stages import run_writer


@pytest.fixture
def completion(monkeypatch):
    model = ChatOpenAI(
        model="deepseek-chat", api_key="offline-placeholder",
        base_url="https://example.invalid/v1", temperature=0,
        use_responses_api=False,
    )
    create = Mock()
    monkeypatch.setattr(model.client.with_raw_response, "create", create)
    monkeypatch.setattr(writer, "get_model", lambda: model)
    return create


@pytest.mark.parametrize("prompt", [
    'Write a report from Evidence: {"title": "Paper", "verified": true}',
    'Revise the draft using Critic feedback and new Evidence: {"id": "E2"}',
])
def test_writer_chain_preserves_input_and_returns_markdown(completion, prompt):
    report = "# Research Report\n\nEvidence supports this conclusion.\n"
    raw = Mock()
    raw.parse.return_value = {
        "id": "offline", "model": "deepseek-chat",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {
            "role": "assistant", "content": report,
        }}],
    }
    completion.return_value = raw

    result = run_writer(prompt)

    assert isinstance(result, str)
    assert result == report
    request = completion.call_args.kwargs
    assert request["messages"] == [
        {"role": "system", "content": writer.WRITER_INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    assert "tools" not in request
    assert "response_format" not in request


def test_writer_propagates_model_failure(completion):
    completion.side_effect = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError, match="model unavailable"):
        run_writer("write report")
