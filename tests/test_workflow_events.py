import pytest

from models.critic_review import CriticReview
from workers.planner import ResearchPlan, ResearchSubQuestion
from workflow.pipeline import run_research_pipeline
from workflow import pipeline


@pytest.mark.parametrize("research_again", [False, True])
def test_real_pipeline_stage_events_follow_execution(monkeypatch, research_again):
    events = []
    def planner(question):
        assert events[-1].stage == "planner" and events[-1].type == "stage_started"
        assert events[-1].message == "正在生成研究计划"
        return ResearchPlan(research_goal="goal", sub_questions=[
            ResearchSubQuestion(id=1, question="query", search_type="paper_search"),
        ])
    monkeypatch.setattr(pipeline, "run_planner", planner)
    monkeypatch.setattr(pipeline, "run_research_query", lambda *a, **k: [])
    monkeypatch.setattr(pipeline, "run_writer", lambda prompt: "Report")
    monkeypatch.setattr(pipeline, "run_critic", lambda prompt: CriticReview(
        overall_assessment="Review", issues=[], evidence_gaps=[], needs_research=research_again,
        research_queries=["followup"] if research_again else [], verdict="PASS",
    ))
    state = run_research_pipeline("question", on_event=events.append)
    assert events[0].type == "workflow_started"
    assert events[-1].type == "workflow_completed"
    assert events[-1].data["report"] == state.final_report
    assert all("report" not in e.data for e in events[:-1])
    starts = [e.stage for e in events if e.type == "stage_started"]
    assert starts == ["planner", "researcher", "writer", "citation_validation", "critic"] + (
        ["re_research"] if research_again else []
    ) + ["revision", "citation_validation", "final_critic"]
    assert [e.stage for e in events if e.type == "stage_completed"] == starts
    assert any(e.type == "progress" and e.stage == "researcher" for e in events)
    assert any(e.type == "warning" and e.stage == "critic" for e in events) == research_again


def test_pipeline_failure_event_is_safe_and_original_exception_propagates(monkeypatch):
    def fail(question):
        raise RuntimeError("secret key and internal path")
    monkeypatch.setattr(pipeline, "run_planner", fail)
    events = []
    with pytest.raises(RuntimeError):
        run_research_pipeline("question", on_event=events.append)
    assert events[-1].type == "workflow_failed"
    assert "secret" not in events[-1].model_dump_json()
