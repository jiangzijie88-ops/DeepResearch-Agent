from models.search_type import SearchType

from workers.researcher import (
    create_researcher_agent,
)


def test_paper_search_creates_only_paper_tool():

    agent = create_researcher_agent(
        SearchType.PAPER_SEARCH
    )

    tool_names = [
        tool.name
        for tool in agent.tools
    ]

    assert (
        "paper_search"
        in tool_names
    )

    assert (
        "web_search"
        not in tool_names
    )


def test_web_search_creates_only_web_tool():

    agent = create_researcher_agent(
        SearchType.WEB_SEARCH
    )

    tool_names = [
        tool.name
        for tool in agent.tools
    ]

    assert (
        "web_search"
        in tool_names
    )

    assert (
        "paper_search"
        not in tool_names
    )


def test_hybrid_creates_two_tools():

    agent = create_researcher_agent(
        SearchType.HYBRID
    )

    tool_names = [
        tool.name
        for tool in agent.tools
    ]

    assert (
        "paper_search"
        in tool_names
    )

    assert (
        "web_search"
        in tool_names
    )