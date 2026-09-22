import json

import pytest

from models.critic_review import CriticReview
from models.evidence import Evidence
from models.research_state import ResearchStatus
from workers.planner import ResearchPlan, ResearchSubQuestion
from workflow import pipeline


@pytest.fixture
def pipeline_case(monkeypatch):
    plan = ResearchPlan(research_goal="测试", sub_questions=[
        ResearchSubQuestion(id=1, question="论文", search_type="paper_search"),
        ResearchSubQuestion(id=2, question="网页", search_type="web_search"),
    ])
    review = CriticReview(overall_assessment="需要修订", issues=[],
                          evidence_gaps=[], needs_research=True,
                          research_queries=[], verdict="PASS_WITH_REVISIONS")
    calls = []
    prompts = []
    results = [
        [Evidence(title="测试论文", evidence_type="paper", source="OpenAlex",
                  doi="10.1000/demo", summary="摘要", citations=2)],
        [Evidence(title="测试论文", evidence_type="paper", source="Semantic Scholar",
                  doi="https://doi.org/10.1000/demo", summary="摘要", citations=8,
                  venue="Demo Journal")],
    ]
    monkeypatch.setattr(pipeline, "run_planner", lambda question: plan)
    monkeypatch.setattr(pipeline, "reset_search_count", lambda: calls.append("reset_web"))
    monkeypatch.setattr(pipeline, "reset_paper_search_count", lambda: calls.append("reset_paper"))

    def research(query, search_type):
        calls.append((query, search_type.value))
        return results.pop(0)

    def writer(prompt):
        prompts.append(prompt)
        return "# 测试报告"

    monkeypatch.setattr(pipeline, "run_research_query", research)
    monkeypatch.setattr(pipeline, "run_writer", writer)
    monkeypatch.setattr(pipeline, "run_critic", lambda report: review)
    return results, prompts, calls


def test_pipeline_merges_duplicate_evidence_before_writing(pipeline_case):
    state = pipeline.run_research_pipeline("测试问题")
    assert len(state.evidence) == 1
    assert state.evidence[0].citations == 8
    assert state.evidence[0].venue == "Demo Journal"
    assert state.evidence[0].source == "OpenAlex | Semantic Scholar"
    prompt = pipeline_case[1][0]
    evidence, _ = json.JSONDecoder().raw_decode(prompt[prompt.index("["):])
    assert len(evidence) == 1
    assert evidence[0]["title"] == "测试论文"
    assert evidence[0]["citations"] == 8


def test_pipeline_completes_even_when_critic_requests_revision(
    pipeline_case
):

    state = (
        pipeline.run_research_pipeline(
            "测试问题"
        )
    )

    assert (
        state.status
        == ResearchStatus.COMPLETED
    )

    assert (
        state.draft_report
        == "# 测试报告"
    )

    assert (
        state.final_report
        == "# 测试报告"
    )

    assert (
        state.critic_review.needs_research
        is True
    )

    assert (
        state.final_review
        is not None
    )


def test_pipeline_resets_both_budgets_before_each_query(pipeline_case):
    pipeline.run_research_pipeline("测试问题")
    assert pipeline_case[2] == [
        "reset_web", "reset_paper", ("论文", "paper_search"),
        "reset_web", "reset_paper", ("网页", "web_search"),
    ]


def test_pipeline_handles_empty_evidence(pipeline_case):
    pipeline_case[0][:] = [[], []]
    state = pipeline.run_research_pipeline("没有结果")
    assert state.evidence == []
    assert state.status == ResearchStatus.COMPLETED
    assert "[]" in pipeline_case[1][0]


def test_pipeline_emits_ordered_events(pipeline_case):
    events = []
    pipeline.run_research_pipeline("测试问题", callback=events.append)
    assert events == [
        "Planner started", "Researcher started",
        "Researching sub-question 1: 论文", "Researching sub-question 2: 网页",
        "Writer started", "Critic started", "Research completed",
    ]
