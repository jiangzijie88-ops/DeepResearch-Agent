from models.search_type import SearchType

from workflow.tool_router import (
    ToolRouter,
)


def test_research_stage_can_get_allowed_tools_from_router():

    router = ToolRouter()

    routed = router.route(
        SearchType.PAPER_SEARCH
    )

    assert (
        routed.tools
        ==
        [
            "paper_search"
        ]
    )


def test_hybrid_question_gets_two_tools():

    router = ToolRouter()

    routed = router.route(
        SearchType.HYBRID
    )

    assert (
        routed.tools
        ==
        [
            "paper_search",
            "web_search",
        ]
    )