from models.search_type import SearchType

from workflow.tool_router import (
    ToolRouter,
    RoutedTools,
)


def test_paper_search_routes_to_paper_tool():

    router = ToolRouter()

    result = router.route(
        SearchType.PAPER_SEARCH
    )

    assert isinstance(
        result,
        RoutedTools,
    )

    assert (
        result.tools
        == [
            "paper_search"
        ]
    )


def test_web_search_routes_to_web_tool():

    router = ToolRouter()

    result = router.route(
        SearchType.WEB_SEARCH
    )

    assert (
        result.tools
        == [
            "web_search"
        ]
    )


def test_hybrid_routes_to_two_tools():

    router = ToolRouter()

    result = router.route(
        SearchType.HYBRID
    )

    assert (
        result.tools
        == [
            "paper_search",
            "web_search",
        ]
    )


def test_router_rejects_invalid_type():

    router = ToolRouter()

    try:
        router.route(
            "invalid"
        )

        assert False

    except ValueError:
        assert True



def test_router_accepts_raw_string():

    router = ToolRouter()

    result = router.route(
        "paper_search"
    )

    assert (
        result.tools
        == [
            "paper_search"
        ]
    )