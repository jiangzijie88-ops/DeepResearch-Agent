"""Run all real role chains and persistence with only remote calls replaced."""

import json
from unittest.mock import Mock

from langchain_openai import ChatOpenAI

from memory import MemoryItem, load_memory, save_memory
from models.academic_paper import AcademicPaper
from models.research_state import ResearchStatus
from models.state_store import load_state
from workers import critic, planner, researcher, writer
from workflow.pipeline import run_research_pipeline
import tools.paper_search as papers


def response(content=None, function=None, arguments=None):
    message = {"role": "assistant", "content": content}
    if function:
        message["tool_calls"] = [{
            "id": "offline-call", "type": "function",
            "function": {"name": function, "arguments": json.dumps(arguments)},
        }]
    raw = Mock()
    raw.parse.return_value = {
        "id": "offline", "model": "deepseek-chat",
        "choices": [{"index": 0, "finish_reason": "tool_calls" if function else "stop",
                     "message": message}],
    }
    return raw


def test_full_langchain_pipeline_with_reresearch_memory_and_resume(monkeypatch, tmp_path):
    model = ChatOpenAI(
        model="deepseek-chat", api_key="offline-placeholder",
        base_url="https://example.invalid/v1", temperature=0, use_responses_api=False,
    )
    for role in (planner, researcher, writer, critic):
        monkeypatch.setattr(role, "get_model", lambda: model)
    monkeypatch.setattr(papers, "_paper_search_count", 0)
    monkeypatch.setattr(papers, "_seen_paper_ids", set())
    title = "Multimodal Recommendation with Graph Neural Networks"
    provider = Mock(side_effect=[
        [AcademicPaper(title=title, year=2025, source="OpenAlex", doi="10.1000/demo", citations=count)]
        for count in (2, 8)
    ])
    monkeypatch.setattr(papers, "search_academic_papers", provider)
    evidence = {"title": title, "evidence_type": "paper", "source": "OpenAlex",
                "doi": "10.1000/demo", "summary": "Supported summary", "verified": True}
    review = {"overall_assessment": "Check citations", "issues": [], "evidence_gaps": [],
              "needs_research": True, "research_queries": ["follow-up query"],
              "verdict": "PASS_WITH_REVISIONS"}
    final_review = dict(review, needs_research=False, research_queries=[], verdict="PASS")
    create = Mock(side_effect=[
        response(function="ResearchPlan", arguments={"research_goal": "goal", "sub_questions": [
            {"id": 1, "question": "initial query", "search_type": "paper_search"},
        ]}),
        response(function="paper_search", arguments={"query": "initial query", "start_year": 2024, "end_year": 2026}),
        response(json.dumps({"evidence": [dict(evidence, citations=2)]})),
        response("# Draft report"),
        response(function="CriticReview", arguments=review),
        response(function="paper_search", arguments={"query": "follow-up query", "start_year": 2024, "end_year": 2026}),
        response(json.dumps({"evidence": [dict(evidence, citations=8)]})),
        response("# Final report"),
        response(function="CriticReview", arguments=final_review),
    ])
    monkeypatch.setattr(model.client.with_raw_response, "create", create)
    state_path, memory_path = tmp_path / "state.json", tmp_path / "memory.json"
    save_memory([MemoryItem(question="research topic", summary="Remembered result")], memory_path)

    state = run_research_pipeline("research topic", state_path=state_path, memory_path=memory_path)

    assert state.status == ResearchStatus.COMPLETED
    assert state.draft_report == "# Draft report"
    assert state.final_report == "# Final report"
    assert state.critic_review.needs_research is True
    assert state.final_review.verdict == "PASS"
    assert len(state.evidence) == 1 and state.evidence[0].citations == 8
    assert state.research_round == 1
    assert provider.call_count == 2 and create.call_count == 9
    assert "Remembered result" in create.call_args_list[0].kwargs["messages"][1]["content"]
    assert '"citations": 8' in create.call_args_list[7].kwargs["messages"][1]["content"]
    memories = load_memory(memory_path)
    assert len(memories) == 2 and memories[-1].summary == "# Final report"
    saved = load_state(state_path)
    assert saved.model_dump() == state.model_dump()
    assert run_research_pipeline(state=saved).final_report == "# Final report"
    assert create.call_count == 9  # Completed Resume must not repeat model calls.
