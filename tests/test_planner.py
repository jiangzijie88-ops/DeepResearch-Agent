"""Exercise the real Planner chain and parser with an offline model response."""

import json
from unittest.mock import Mock

import pytest
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from workers import planner
from workflow import stages


@pytest.fixture
def completion(monkeypatch):
    model = ChatOpenAI(
        model="deepseek-chat", api_key="offline-placeholder",
        base_url="https://example.invalid/v1", temperature=0,
        use_responses_api=False,
    )
    create = Mock()
    monkeypatch.setattr(model.client.with_raw_response, "create", create)
    monkeypatch.setattr(planner, "get_model", lambda: model)
    return create


def respond(completion, plan):
    raw = Mock()
    raw.parse.return_value = {
        "id": "offline", "model": "deepseek-chat",
        "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": None, "tool_calls": [{
                "id": "plan_1", "type": "function", "function": {
                    "name": "ResearchPlan", "arguments": json.dumps(plan),
                },
            }],
        }}],
    }
    completion.return_value = raw


def test_planner_chain_preserves_question_memory_and_search_types(completion):
    respond(completion, {
        "research_goal": "Research goal",
        "sub_questions": [
            {"id": i, "question": kind, "search_type": kind}
            for i, kind in enumerate(("paper_search", "web_search", "hybrid"), 1)
        ],
    })
    plan = stages.run_planner("Question {literal}", 'Memory {"source": "saved"}')
    assert isinstance(plan, planner.ResearchPlan)
    assert [q.search_type.value for q in plan.sub_questions] == [
        "paper_search", "web_search", "hybrid",
    ]
    request = completion.call_args.kwargs
    assert request["messages"][0]["role"] == "system"
    user_message = request["messages"][1]
    assert user_message["role"] == "user"
    assert "Question {literal}" in user_message["content"]
    assert 'Memory {"source": "saved"}' in user_message["content"]
    assert [tool["function"]["name"] for tool in request["tools"]] == ["ResearchPlan"]


def test_planner_rejects_invalid_search_type(completion):
    respond(completion, {
        "research_goal": "goal",
        "sub_questions": [{"id": 1, "question": "question", "search_type": "both"}],
    })
    with pytest.raises(ValidationError):
        stages.run_planner("question")


def test_planner_propagates_model_failure(completion):
    completion.side_effect = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError, match="model unavailable"):
        stages.run_planner("question")
