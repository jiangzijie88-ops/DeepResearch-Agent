from models.research_state import ResearchState, ResearchStatus
from workers.planner import ResearchPlan, ResearchSubQuestion
from models.evidence import Evidence
from models.critic_review import CriticReview, CriticIssue

from memory.memory_item import (
    MemoryItem,
)



def test_research_state_default_values():
    state = ResearchState(
        question="查找 2024 到 2026 年基于 GNN 的多模态推荐论文"
    )

    assert state.question == "查找 2024 到 2026 年基于 GNN 的多模态推荐论文"
    assert state.plan is None
    assert state.evidence == []
    assert state.draft_report is None
    assert state.critic_review is None
    assert state.research_round == 0
    assert state.status == ResearchStatus.INITIALIZED
    assert state.final_report is None
    assert state.final_review is None


def test_research_state_accepts_existing_models():
    plan = ResearchPlan(
        research_goal="收集相关论文",
        sub_questions=[
            ResearchSubQuestion(
                id=1,
                question="查找相关学术论文",
                search_type="paper_search",
            )
        ],
    )

    evidence = Evidence(
        title="Example Paper",
        evidence_type="paper",
        year=2025,
        citations=10,
        source="OpenAlex",
        doi="10.1000/example",
        url="https://example.com",
        summary="用于测试 ResearchState。",
        verified=True,
    )

    critic_review = CriticReview(
        overall_assessment="整体质量良好",
        issues=[
            CriticIssue(
                issue_type="missing_evidence",
                description="缺少部分证据",
                suggestion="继续补充检索",
            )
        ],
        evidence_gaps=["缺少 2026 年论文"],
        needs_research=True,
        research_queries=["查找 2026 年相关论文"],
        verdict="PASS_WITH_REVISIONS",
    )

    state = ResearchState(
        question="测试问题",
        plan=plan,
        evidence=[evidence],
        draft_report="第一版报告",
        critic_review=critic_review,
        research_round=1,
        status=ResearchStatus.REVIEWING,
        final_report="最终报告",
        final_review=critic_review,
    )

    assert state.plan == plan
    assert state.evidence == [evidence]
    assert state.critic_review == critic_review
    assert state.research_round == 1
    assert state.status == ResearchStatus.REVIEWING
    assert state.final_report == "最终报告"
    assert state.final_review == critic_review




def test_research_state_can_store_plan_and_update_status():
    state = ResearchState(
        question="测试 Planner 状态流"
    )

    plan = ResearchPlan(
        research_goal="完成测试研究计划",
        sub_questions=[
            ResearchSubQuestion(
                id=1,
                question="测试子问题",
                search_type="paper_search",
            )
        ],
    )

    state.plan = plan
    state.status = ResearchStatus.PLANNED

    assert state.plan == plan
    assert state.status == ResearchStatus.PLANNED


def test_research_state_can_store_evidence_and_update_status():
    state = ResearchState(
        question="测试 Researcher 状态流"
    )

    evidence = Evidence(
        title="Example Research Paper",
        evidence_type="paper",
        year=2025,
        citations=12,
        source="OpenAlex",
        doi="10.1000/example-paper",
        url="https://example.com/paper",
        summary="用于测试 ResearchState 的 Evidence 存储。",
        verified=True,
    )

    state.status = ResearchStatus.RESEARCHING
    state.evidence = [evidence]

    assert state.status == ResearchStatus.RESEARCHING
    assert len(state.evidence) == 1
    assert state.evidence[0] == evidence
    assert state.evidence[0].title == "Example Research Paper"


def test_research_state_can_store_draft_report_and_update_status():
    state = ResearchState(
        question="测试 Writer 状态流"
    )

    draft_report = "# Research Report\n\n这是第一版研究报告。"

    state.status = ResearchStatus.WRITING
    state.draft_report = draft_report

    assert state.status == ResearchStatus.WRITING
    assert state.draft_report == draft_report



def test_research_state_can_store_critic_review_and_update_status():
    state = ResearchState(
        question="测试 Critic 状态流"
    )

    critic_review = CriticReview(
        overall_assessment="报告整体可用，但仍存在证据缺口。",
        issues=[
            CriticIssue(
                issue_type="evidence_gap",
                description="缺少部分 2026 年证据。",
                suggestion="补充检索 2026 年论文。",
            )
        ],
        evidence_gaps=[
            "缺少 2026 年论文"
        ],
        needs_research=True,
        research_queries=[
            "查找 2026 年 GNN 多模态推荐论文"
        ],
        verdict="PASS_WITH_REVISIONS",
    )

    state.status = ResearchStatus.REVIEWING
    state.critic_review = critic_review

    assert state.status == ResearchStatus.REVIEWING
    assert state.critic_review == critic_review
    assert state.critic_review.needs_research is True
    assert len(state.critic_review.research_queries) == 1



def test_research_state_can_track_research_round():
    state = ResearchState(
        question="测试补搜轮次"
    )

    assert state.research_round == 0

    state.status = ResearchStatus.RE_RESEARCHING
    state.research_round += 1

    assert state.status == ResearchStatus.RE_RESEARCHING
    assert state.research_round == 1


def test_research_state_can_store_final_report_and_final_review():
    state = ResearchState(
        question="测试最终状态"
    )

    final_review = CriticReview(
        overall_assessment="最终报告可交付。",
        issues=[],
        evidence_gaps=[],
        needs_research=False,
        research_queries=[],
        verdict="PASS",
    )

    state.final_report = "最终研究报告"
    state.final_review = final_review
    state.status = ResearchStatus.COMPLETED

    assert state.final_report == "最终研究报告"
    assert state.final_review == final_review
    assert state.status == ResearchStatus.COMPLETED


def test_research_status_supports_revision():
    assert ResearchStatus.REVISING.value == "revising"


def test_research_status_supports_final_review():
    assert ResearchStatus.FINAL_REVIEWING.value == "final_reviewing"


def test_research_state_can_store_tool_routes():

    state = ResearchState(
        question="tool route test"
    )

    state.tool_routes = {
        "1": [
            "paper_search"
        ]
    }


    assert (
        state.tool_routes["1"]
        ==
        [
            "paper_search"
        ]
    )


def test_build_memory_context():

    from memory.memory_context import (
        build_memory_context,
    )


    memories = [

        MemoryItem(
            question=
            "GNN multimodal recommendation",

            summary=
            "Found LGMRec",
            
            evidence_count=3,
        )

    ]


    context = build_memory_context(
        memories,
        "GNN",
    )


    assert (
        "LGMRec"
        in
        context
    )


def test_build_memory_context_empty():

    from memory.memory_context import (
        build_memory_context,
    )


    context = build_memory_context(
        [],
        "unknown",
    )


    assert (
        "No previous"
        in
        context
    )