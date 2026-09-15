from models.research_state import ResearchState, ResearchStatus
from models.state_store import save_state, load_state
from models.evidence import Evidence
from models.critic_review import CriticReview
from workers.planner import ResearchPlan, ResearchSubQuestion


def test_save_and_load_research_state(tmp_path):
    plan = ResearchPlan(
        research_goal="测试状态持久化",
        sub_questions=[
            ResearchSubQuestion(
                id=1,
                question="测试子问题",
                search_type="paper_search",
            )
        ],
    )

    evidence = Evidence(
        title="Persistent Paper",
        evidence_type="paper",
        year=2025,
        citations=8,
        source="OpenAlex",
        doi="10.1000/persistent",
        url="https://example.com/persistent",
        summary="用于测试状态保存与恢复。",
        verified=True,
    )

    critic_review = CriticReview(
        overall_assessment="报告基本可用。",
        issues=[],
        evidence_gaps=[],
        needs_research=False,
        research_queries=[],
        verdict="PASS",
    )

    original_state = ResearchState(
        question="测试 ResearchState Persistence",
        plan=plan,
        evidence=[evidence],
        draft_report="第一版报告",
        critic_review=critic_review,
        research_round=1,
        status=ResearchStatus.COMPLETED,
        final_report="最终报告",
        final_review=critic_review,
    )

    state_path = tmp_path / "state.json"

    save_state(
        original_state,
        state_path,
    )

    loaded_state = load_state(
        state_path
    )

    assert state_path.exists()
    assert loaded_state == original_state
    assert loaded_state.status == ResearchStatus.COMPLETED
    assert loaded_state.plan == plan
    assert loaded_state.evidence == [evidence]
    assert loaded_state.final_review == critic_review


def test_save_state_overwrites_with_latest_state(tmp_path):
    state_path = tmp_path / "state.json"

    state = ResearchState(
        question="测试 checkpoint 覆盖"
    )

    save_state(
        state,
        state_path,
    )

    state.status = ResearchStatus.PLANNED

    save_state(
        state,
        state_path,
    )

    state.status = ResearchStatus.RESEARCHING
    state.research_round = 1

    save_state(
        state,
        state_path,
    )

    loaded_state = load_state(
        state_path
    )

    assert loaded_state.status == ResearchStatus.RESEARCHING
    assert loaded_state.research_round == 1
    assert loaded_state.question == "测试 checkpoint 覆盖"


def test_state_store_preserves_evidence_provenance(
    tmp_path,
):
    from models.evidence import Evidence

    evidence = Evidence(
        title="State Provenance Paper",
        evidence_type="paper",
        year=2025,
        citations=5,
        source="OpenAlex",
        doi=None,
        url="https://example.com/state",
        summary="测试 checkpoint provenance。",
        verified=True,
        query="state query",
        retrieved_at="2026-08-31T02:30:00+00:00",
    )

    state = ResearchState(
        question="test",
        evidence=[evidence],
    )

    path = tmp_path / "state.json"

    save_state(
        state,
        path,
    )

    loaded = load_state(
        path
    )

    loaded_evidence = loaded.evidence[0]

    assert (
        loaded_evidence.query
        == "state query"
    )

    assert (
        loaded_evidence.retrieved_at
        == "2026-08-31T02:30:00+00:00"
    )


from models.search_type import SearchType
from workers.planner import (
    ResearchPlan,
    ResearchSubQuestion,
)


def test_state_store_preserves_search_type_enum(
    tmp_path,
):
    state_path = (
        tmp_path
        / "search_type_state.json"
    )

    state = ResearchState(
        question="routing test",
        plan=ResearchPlan(
            research_goal=(
                "Test search type persistence."
            ),
            sub_questions=[
                ResearchSubQuestion(
                    id=1,
                    question=(
                        "Find academic papers."
                    ),
                    search_type=(
                        SearchType.PAPER_SEARCH
                    ),
                )
            ],
        ),
    )

    save_state(
        state,
        state_path,
    )

    loaded = load_state(
        state_path
    )

    assert (
        loaded
        .plan
        .sub_questions[0]
        .search_type
        == SearchType.PAPER_SEARCH
    )
