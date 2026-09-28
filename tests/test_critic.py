"""Exercise Critic's real structured chain with offline completion responses."""

import json
from unittest.mock import Mock

import pytest
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from models.critic_review import CriticIssue, CriticReview
from workers import critic
from workflow.stages import run_critic


@pytest.fixture
def completion(monkeypatch):
    model = ChatOpenAI(
        model="deepseek-chat", api_key="offline-placeholder",
        base_url="https://example.invalid/v1", temperature=0,
        use_responses_api=False,
    )
    create = Mock()
    monkeypatch.setattr(model.client.with_raw_response, "create", create)
    monkeypatch.setattr(critic, "get_model", lambda: model)
    return create


def respond(completion, review):
    raw = Mock()
    raw.parse.return_value = {
        "id": "offline", "model": "deepseek-chat",
        "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": None, "tool_calls": [{
                "id": "review_1", "type": "function", "function": {
                    "name": "CriticReview", "arguments": json.dumps(review),
                },
            }],
        }}],
    }
    completion.return_value = raw


@pytest.mark.parametrize("verdict,needs_research", [
    ("PASS", False), ("PASS_WITH_REVISIONS", True), ("FAIL", True),
])
def test_critic_parses_review_and_preserves_evidence(completion, verdict, needs_research):
    data = {
        "overall_assessment": "Review assessment",
        "issues": [{
            "issue_type": "missing_evidence", "description": "Missing source",
            "suggestion": "Find supporting evidence",
        }] if needs_research else [],
        "evidence_gaps": ["Missing source"] if needs_research else [],
        "needs_research": needs_research,
        "research_queries": ["Find supporting source"] if needs_research else [],
        "verdict": verdict,
    }
    respond(completion, data)
    prompt = 'Review report and Evidence: {"id": "E1", "verified": false}'
    review = run_critic(prompt)
    assert isinstance(review, CriticReview)
    assert review.model_dump() == data
    if needs_research:
        assert isinstance(review.issues[0], CriticIssue)
    request = completion.call_args.kwargs
    assert request["messages"] == [
        {"role": "system", "content": critic.CRITIC_INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    # The schema tool formats the response; no search tools are available.
    assert [tool["function"]["name"] for tool in request["tools"]] == ["CriticReview"]


def test_critic_rejects_missing_required_fields(completion):
    respond(completion, {"overall_assessment": "Incomplete review"})
    with pytest.raises(ValidationError):
        run_critic("Review report")


def test_critic_propagates_model_failure(completion):
    completion.side_effect = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError, match="model unavailable"):
        run_critic("Review report")


def test_critic_retries_a_response_without_the_review_tool(completion):
    review = {
        "overall_assessment": "Supported", "issues": [], "evidence_gaps": [],
        "needs_research": False, "research_queries": [], "verdict": "PASS",
    }
    respond(completion, review)
    valid = completion.return_value
    missing_tool = Mock()
    missing_tool.parse.return_value = {
        "id": "offline", "model": "deepseek-chat",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {
            "role": "assistant", "content": "The report is supported.",
        }}],
    }
    completion.side_effect = [missing_tool, valid]
    assert run_critic("Review report").verdict == "PASS"
    assert completion.call_count == 2
