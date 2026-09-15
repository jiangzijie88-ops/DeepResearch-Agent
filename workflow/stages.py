import json

from datetime import datetime, timezone

from agents import Runner


from workers.planner import (
    planner_agent,
    ResearchPlan,
)


from workflow.tool_router import (
    ToolRouter,
)


from workers.researcher_factory import (
    create_researcher_agent,
)


from workers.writer import (
    writer_agent,
)


from workers.critic import (
    critic_agent,
)


from models.evidence import Evidence


from models.critic_review import (
    CriticReview,
)


from models.search_type import (
    SearchType,
)

def safe_json_loads(
    text: str,
):

    text = text.strip()

    if not text:

        return {
            "evidence": []
        }

    if "```json" in text:

        text = (
            text
            .split("```json", 1)[1]
            .split("```", 1)[0]
            .strip()
        )


    elif "```" in text:

        text = (
            text
            .split("```", 1)[1]
            .split("```", 1)[0]
            .strip()
        )


    start = text.find("{")
    end = text.rfind("}")


    if (
        start != -1
        and end != -1
    ):

        text = text[
            start:end + 1
        ]


    try:

        return json.loads(
            text
        )


    except json.JSONDecodeError:

        print(
            "\n[JSON PARSE FAILED]"
        )

        print(
            text
        )

        raise



def utc_now():
    return datetime.now(
        timezone.utc
    )



def run_planner(
    question: str,
    memory_context: str = "",
    runner=Runner,
) -> ResearchPlan:

    planner_prompt = f"""
    用户研究问题：

    {question}


    历史研究记忆：

    {memory_context}


    请基于用户问题和已有研究记忆，
    生成新的 Research Plan。

    如果历史记忆为空，
    不要假设已有知识。
    """



    result = runner.run_sync(
        planner_agent,
        planner_prompt,
        max_turns=3,
    )


    raw_plan = result.final_output


    plan_dict = safe_json_loads(
        raw_plan
    )


    return ResearchPlan.model_validate(
        plan_dict
    )



def run_writer(
    prompt: str,
    runner=Runner,
) -> str:

    result = runner.run_sync(
        writer_agent,
        prompt,
        max_turns=3,
    )


    return result.final_output



def run_critic(
    prompt: str,
    runner=Runner,
) -> CriticReview:

    result = runner.run_sync(
        critic_agent,
        prompt,
        max_turns=3,
    )


    raw_review = result.final_output


    review_dict = safe_json_loads(
        raw_review
    )


    return CriticReview.model_validate(
        review_dict
    )



def run_research_query(
    query: str,
    search_type=None,
    runner=Runner,
    clock=utc_now,
) -> list[Evidence]:


    # ===============================
    # Step 7C:
    # Planner search_type
    #        ↓
    # ToolRouter
    #        ↓
    # allowed tools
    # ===============================

    router = ToolRouter()


    # 保持旧代码兼容
    # 如果没有传 search_type，
    # 默认按照旧逻辑走论文搜索

    if search_type is None:

        search_type = (
            SearchType.PAPER_SEARCH
        )


    routed_tools = router.route(
        search_type
    )


    # ===============================
    # Step 7D:
    #
    # SearchType
    #       ↓
    # ToolRouter
    #       ↓
    # Dynamic Researcher Agent
    # ===============================

    researcher_agent = (
        create_researcher_agent(
            search_type
        )
    )


    result = runner.run_sync(
        researcher_agent,
        query,
        max_turns=8,
    )


    raw_output = result.final_output


    try:

        data = safe_json_loads(
            raw_output
        )


    except json.JSONDecodeError:

        data = {
            "evidence": []
        }

    evidence_list = []


    for item in data.get(
        "evidence",
        []
    ):


        item.setdefault(
            "evidence_type",
            "paper",
        )


        item.setdefault(
            "source",
            "OpenAlex",
        )


        item.setdefault(
            "summary",
            item.get(
                "abstract",
                "",
            ),
        )


        evidence_list.append(
            Evidence.model_validate(
                item
            )
        )



    retrieved_at = (

        clock()

        .isoformat(
            timespec="seconds"
        )

    )



    for evidence in evidence_list:

        evidence.query = query

        evidence.retrieved_at = (
            retrieved_at
        )



    return evidence_list