"""Test actual LangChain tool dispatch with offline ChatOpenAI completions."""

import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from models.search_type import SearchType
from workers import researcher
from workflow.stages import run_research_query


def reply(content=None, calls=()):
    raw = Mock()
    message = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = [
            {"id": call_id, "type": "function", "function": {
                "name": name, "arguments": json.dumps(args),
            }} for call_id, name, args in calls
        ]
    raw.parse.return_value = {
        "id": "offline", "model": "deepseek-chat",
        "choices": [{"index": 0, "finish_reason": "tool_calls" if calls else "stop",
                     "message": message}],
    }
    return raw


@pytest.fixture
def setup_agent(monkeypatch):
    model = ChatOpenAI(
        model="deepseek-chat", api_key="offline-placeholder",
        base_url="https://example.invalid/v1", temperature=0,
        use_responses_api=False,
    )
    create = Mock()
    monkeypatch.setattr(model.client.with_raw_response, "create", create)
    monkeypatch.setattr(researcher, "get_model", lambda: model)
    executed = []

    @tool
    def paper_search(query: str, start_year: int, end_year: int) -> str:
        """Search academic sources."""
        executed.append(("paper_search", query, start_year, end_year))
        return "Title: Paper A\nSource: OpenAlex\nAuthors: Alice"

    @tool
    def web_search(query: str) -> str:
        """Search web sources."""
        executed.append(("web_search", query))
        return "Title: Website B\nURL: https://example.invalid"

    monkeypatch.setattr(researcher, "paper_search", paper_search)
    monkeypatch.setattr(researcher, "web_search", web_search)
    return create, executed


def test_hybrid_executes_tools_feeds_results_back_and_returns_evidence(setup_agent):
    create, executed = setup_agent
    create.side_effect = [
        reply(calls=[
            ("paper_1", "paper_search", {"query": "academic query", "start_year": 2024, "end_year": 2026}),
            ("web_1", "web_search", {"query": "web query"}),
        ]),
        reply(json.dumps({"evidence": [{
            "title": "Paper A", "evidence_type": "paper", "source": "OpenAlex",
            "summary": "Relevant paper", "authors": ["Alice"], "verified": True,
            "query": "invented", "retrieved_at": "invented",
        }]})),
    ]
    evidence = run_research_query(
        "original query {literal}", SearchType.HYBRID,
        clock=lambda: datetime(2026, 9, 22, tzinfo=timezone.utc),
    )
    assert executed == [("paper_search", "academic query", 2024, 2026), ("web_search", "web query")]
    assert evidence[0].authors == ["Alice"]
    assert evidence[0].query == "original query {literal}"
    assert evidence[0].retrieved_at == "2026-09-22T00:00:00+00:00"
    first = create.call_args_list[0].kwargs
    assert first["tool_choice"] == "required"
    assert {t["function"]["name"] for t in first["tools"]} == {"paper_search", "web_search"}
    messages = create.call_args_list[1].kwargs["messages"]
    results = [m for m in messages if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in results] == ["paper_1", "web_1"]
    assert "Paper A" in results[0]["content"]
    assert "Website B" in results[1]["content"]


@pytest.mark.parametrize("bad_name,bad_args", [
    ("paper_search", {"query": "not allowed", "start_year": 2024, "end_year": 2026}),
    ("web_search", {}),
])
def test_disallowed_or_invalid_call_is_not_executed_and_can_recover(setup_agent, bad_name, bad_args):
    create, executed = setup_agent
    create.side_effect = [
        reply(calls=[("bad", bad_name, bad_args)]),
        reply(calls=[("good", "web_search", {"query": "allowed"})]),
        reply('{"evidence": []}'),
    ]
    assert run_research_query("query", SearchType.WEB_SEARCH) == []
    assert executed == [("web_search", "allowed")]
    error = [m for m in create.call_args_list[1].kwargs["messages"] if m["role"] == "tool"][0]
    assert error["tool_call_id"] == "bad"
    assert "Error" in error["content"]


def test_no_tool_call_cannot_produce_unsupported_evidence(setup_agent):
    create, executed = setup_agent
    create.return_value = reply('{"evidence": [{"title": "Invented"}]}')
    assert run_research_query("query", SearchType.WEB_SEARCH) == []
    assert executed == []


def test_tool_loop_stops_at_eight_model_turns(setup_agent):
    create, executed = setup_agent
    create.side_effect = [reply(calls=[(str(i), "web_search", {"query": "q"})]) for i in range(8)]
    assert run_research_query("query", SearchType.WEB_SEARCH) == []
    assert create.call_count == 8
    assert len(executed) == 8


def test_tool_exception_is_returned_to_model(monkeypatch, setup_agent):
    create, _ = setup_agent

    @tool
    def web_search(query: str) -> str:
        """Search failing provider."""
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(researcher, "web_search", web_search)
    create.side_effect = [reply(calls=[("failed", "web_search", {"query": "q"})]), reply('{"evidence": []}')]
    assert run_research_query("query", SearchType.WEB_SEARCH) == []
    messages = create.call_args_list[1].kwargs["messages"]
    assert "Error" in messages[-1]["content"]


def test_model_failure_propagates(setup_agent):
    create, _ = setup_agent
    create.side_effect = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError, match="model unavailable"):
        run_research_query("query", SearchType.WEB_SEARCH)
