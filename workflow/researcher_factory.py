from agents import Agent

from llm import get_model

from models.search_type import SearchType

from tools.web_search import (
    web_search,
)

from tools.paper_search import (
    paper_search,
)

from skills.loader import load_skill


academic_search_skill = load_skill(
    "academic_search"
)


def create_researcher_agent(
    search_type: SearchType,
):

    if isinstance(
        search_type,
        str,
    ):
        search_type = SearchType(
            search_type
        )


    tools = []


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
            f"Unsupported search type:"
            f"{search_type}"
        )


    return Agent(
        name="Researcher",

        instructions=f"""
你是 DeepResearch 系统中的 Researcher Agent。

你的职责是执行 Planner 分配的研究子问题。

只能使用系统提供的工具。

不要编造信息。

只输出结构化 Evidence JSON。

=========================

ACADEMIC SEARCH SKILL

{academic_search_skill}

""",

        model=get_model(),

        tools=tools,
    )