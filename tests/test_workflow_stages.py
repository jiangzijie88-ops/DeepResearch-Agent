from workers.planner import ResearchPlan
from langchain_core.runnables import RunnableLambda
from datetime import datetime, timezone

from models.critic_review import CriticReview
from models.evidence import Evidence

from workflow.stages import (
    run_planner,
    run_writer,
    run_critic,
    run_research_query,
)


def test_run_planner_returns_research_plan():
    def fake_planner(inputs):
        assert inputs == {"question": "测试问题", "memory_context": ""}
        return ResearchPlan.model_validate({
            "research_goal": "测试研究目标",
            "sub_questions": [{
                "id": 1, "question": "测试子问题", "search_type": "paper_search",
            }],
        })

    plan = run_planner(
        question="测试问题",
        runner=RunnableLambda(fake_planner),
    )

    assert isinstance(
        plan,
        ResearchPlan,
    )

    assert (
        plan.research_goal
        == "测试研究目标"
    )

    assert len(
        plan.sub_questions
    ) == 1

    assert (
        plan.sub_questions[0].question
        == "测试子问题"
    )

    assert (
        plan.sub_questions[0].search_type
        == "paper_search"
    )


def test_run_writer_returns_report_text():
    def fake_writer(inputs):
        assert inputs == {"prompt": "测试 Writer 输入"}
        return "这是测试 Writer 生成的报告。"

    report = run_writer(
        prompt="测试 Writer 输入",
        runner=RunnableLambda(fake_writer),
    )

    assert (
        report
        == "这是测试 Writer 生成的报告。"
    )


def test_run_critic_returns_critic_review():
    def fake_critic(inputs):
        assert inputs == {"prompt": "测试 Critic 输入"}
        return CriticReview(
            overall_assessment="报告整体可用。",
            issues=[], evidence_gaps=[], needs_research=False,
            research_queries=[], verdict="PASS",
        )

    review = run_critic(
        prompt="测试 Critic 输入",
        runner=RunnableLambda(fake_critic),
    )

    assert isinstance(
        review,
        CriticReview,
    )

    assert (
        review.overall_assessment
        == "报告整体可用。"
    )

    assert (
        review.needs_research
        is False
    )

    assert (
        review.verdict
        == "PASS"
    )

    assert (
        review.research_queries
        == []
    )

class FakeResearcherExecutor:
    @staticmethod
    def invoke(query, max_turns=8):
        class Result:
            final_output = """
            {
                "evidence": [
                    {
                        "title": "Test Paper",
                        "evidence_type": "paper",
                        "year": 2025,
                        "citations": 12,
                        "source": "OpenAlex",
                        "doi": "10.1000/test",
                        "url": "https://example.com/test",
                        "summary": "用于测试 Researcher Stage。",
                        "verified": true,
                        "authors": [
                            "Alice Zhang",
                            "Bob Li"
                        ],
                        "venue": "SIGIR",
                        "published_at": "2025-07-15"
                    }
                ]
            }
            """

        return Result.final_output


def fake_clock():
    return datetime(
        2026,
        8,
        31,
        2,
        30,
        0,
        tzinfo=timezone.utc,
    )

def test_run_research_query_returns_evidence_list():
    evidence_list = run_research_query(
        query="测试论文检索",
        runner=FakeResearcherExecutor,
        clock=fake_clock,
    )

    assert isinstance(
        evidence_list,
        list,
    )

    assert len(
        evidence_list
    ) == 1

    assert isinstance(
        evidence_list[0],
        Evidence,
    )

    assert (
        evidence_list[0].title
        == "Test Paper"
    )

    assert (
        evidence_list[0].year
        == 2025
    )

    assert (
        evidence_list[0].citations
        == 12
    )

    assert (
        evidence_list[0].verified
        is True
    )

    assert (
        evidence_list[0].query
        == "测试论文检索"
    )

    assert (
        evidence_list[0].retrieved_at
        == "2026-08-31T02:30:00+00:00"
    )

    assert evidence_list[0].authors == [
    "Alice Zhang",
    "Bob Li",
]

    assert evidence_list[0].venue == "SIGIR"

    assert (
        evidence_list[0].published_at
        == "2025-07-15"
    )


class FakeEmptyResearcherExecutor:
    @staticmethod
    def invoke(query, max_turns=8):
        class Result:
            final_output = """
            {
                "evidence": []
            }
            """

        return Result.final_output


def test_run_research_query_accepts_empty_evidence():
    evidence_list = run_research_query(
        query="没有结果的测试",
        runner=FakeEmptyResearcherExecutor,
    )

    assert evidence_list == []


class FakeInvalidResearcherExecutor:
    @staticmethod
    def invoke(query, max_turns=8):
        class Result:
            final_output = "not valid json"

        return Result.final_output


def test_run_research_query_returns_empty_evidence_on_invalid_json():

    class FakeResult:

        final_output = (
            "not valid json"
        )


    class FakeExecutor:

        @staticmethod
        def invoke(query, max_turns=8):

            return FakeResult.final_output


    evidence = run_research_query(
        query="test query",
        runner=FakeExecutor,
    )


    assert evidence == []

class FakeInvalidEvidenceExecutor:
    @staticmethod
    def invoke(query, max_turns=8):
        class Result:
            final_output = """
            {
                "evidence": [
                    {
                        "title": "Broken Evidence"
                    }
                ]
            }
            """

        return Result.final_output


class FakeInvalidEvidenceExecutor:
    @staticmethod
    def invoke(query, max_turns=8):
        class Result:
            final_output = """
            {
                "evidence": [
                    {
                        "title": "Broken Evidence"
                    }
                ]
            }
            """

        return Result.final_output


class FakeResearcherWithWrongMetadataExecutor:
    @staticmethod
    def invoke(query, max_turns=8):
        class Result:
            final_output = """
            {
                "evidence": [
                    {
                        "title": "Metadata Test Paper",
                        "evidence_type": "paper",
                        "year": 2025,
                        "citations": 3,
                        "source": "OpenAlex",
                        "doi": null,
                        "url": "https://example.com/metadata",
                        "summary": "测试系统元数据覆盖。",
                        "verified": true,
                        "query": "LLM invented query",
                        "retrieved_at": "2000-01-01T00:00:00"
                    }
                ]
            }
            """

        return Result.final_output


def test_run_research_query_overrides_system_metadata():
    evidence_list = run_research_query(
        query="真实查询词",
        runner=FakeResearcherWithWrongMetadataExecutor,
        clock=fake_clock,
    )

    evidence = evidence_list[0]

    assert evidence.query == "真实查询词"

    assert (
        evidence.retrieved_at
        == "2026-08-31T02:30:00+00:00"
    )


class FakeResearcherWithoutAcademicMetadata:
    @staticmethod
    def invoke(query, max_turns=8):
        class Result:
            final_output = """
            {
                "evidence": [
                    {
                        "title": "Web Evidence",
                        "evidence_type": "web",
                        "year": 2025,
                        "citations": null,
                        "source": "Web",
                        "doi": null,
                        "url": "https://example.com/web",
                        "summary": "普通 Web Evidence。",
                        "verified": false
                    }
                ]
            }
            """

        return Result.final_output



def test_run_research_query_keeps_missing_metadata_empty():
    evidence_list = run_research_query(
        query="web metadata test",
        runner=FakeResearcherWithoutAcademicMetadata,
        clock=fake_clock,
    )

    evidence = evidence_list[0]

    assert evidence.authors == []
    assert evidence.venue is None
    assert evidence.published_at is None


def test_run_planner_accepts_memory_context():

    from workflow.stages import run_planner


    assert callable(
        run_planner
    )
