import pytest

from pydantic import ValidationError

from models.search_type import SearchType

from workers.planner import (
    ResearchSubQuestion,
    ResearchPlan,
)


def test_search_type_has_supported_values():
    assert (
        SearchType.PAPER_SEARCH.value
        == "paper_search"
    )

    assert (
        SearchType.WEB_SEARCH.value
        == "web_search"
    )

    assert (
        SearchType.HYBRID.value
        == "hybrid"
    )


def test_research_sub_question_accepts_paper_search():
    sub_question = ResearchSubQuestion(
        id=1,
        question="Find relevant papers.",
        search_type="paper_search",
    )

    assert (
        sub_question.search_type
        == SearchType.PAPER_SEARCH
    )


def test_research_sub_question_accepts_web_search():
    sub_question = ResearchSubQuestion(
        id=1,
        question="Find current project information.",
        search_type="web_search",
    )

    assert (
        sub_question.search_type
        == SearchType.WEB_SEARCH
    )


def test_research_sub_question_accepts_hybrid():
    sub_question = ResearchSubQuestion(
        id=1,
        question=(
            "Find papers and current "
            "web information."
        ),
        search_type="hybrid",
    )

    assert (
        sub_question.search_type
        == SearchType.HYBRID
    )


def test_research_sub_question_rejects_invalid_search_type():
    with pytest.raises(
        ValidationError,
    ):
        ResearchSubQuestion(
            id=1,
            question="Invalid routing test.",
            search_type="google_search",
        )


def test_research_plan_keeps_legacy_search_type_compatible():
    plan = ResearchPlan.model_validate(
        {
            "research_goal": (
                "Test legacy planner data."
            ),
            "sub_questions": [
                {
                    "id": 1,
                    "question": (
                        "Find academic papers."
                    ),
                    "search_type": (
                        "paper_search"
                    ),
                }
            ],
        }
    )

    assert (
        plan.sub_questions[0].search_type
        == SearchType.PAPER_SEARCH
    )