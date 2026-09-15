from agents import Agent

from llm import get_model

from models.search_type import SearchType

from tools.web_search import web_search
from tools.paper_search import paper_search

from workers.researcher import (
    RESEARCHER_INSTRUCTIONS,
)


def create_researcher_agent(
    search_type: SearchType,
):

    # 兼容旧 checkpoint 中保存的字符串
    if isinstance(
        search_type,
        str,
    ):

        search_type = SearchType(
            search_type
        )


    if (
        search_type
        == SearchType.PAPER_SEARCH
    ):

        tools = [
            paper_search,
        ]


    elif (
        search_type
        == SearchType.WEB_SEARCH
    ):

        tools = [
            web_search,
        ]


    elif (
        search_type
        == SearchType.HYBRID
    ):

        tools = [
            paper_search,
            web_search,
        ]


    else:

        raise ValueError(
            f"Unsupported search type: "
            f"{search_type}"
        )


    return Agent(
        name="Researcher",

        instructions=(
            RESEARCHER_INSTRUCTIONS
        ),

        model=get_model(),

        tools=tools,
    )