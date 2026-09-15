import json

from models.evidence_store import EvidenceStore
from models.research_state import (
    ResearchState,
    ResearchStatus,
)


from workflow.stages import (
    run_planner,
    run_research_query,
    run_writer,
    run_critic,
)

from tools.web_search import (
    reset_search_count,
)

from tools.paper_search import (
    reset_paper_search_count,
)


def emit(
    callback,
    message: str,
):

    if callback:

        callback(message)


def run_research_pipeline(
    question: str,
    callback=None,
):

    state = ResearchState(
        question=question,
    )


    # ======================
    # Step 1 Planner
    # ======================
    emit(
        callback,
        "Planner started",
    )

    plan = run_planner(
        question
    )


    state.plan = plan

    state.status = (
        ResearchStatus.PLANNED
    )


    # ======================
    # Step 2 Research
    # ======================

    evidence_store = EvidenceStore()
    state.status = ResearchStatus.RESEARCHING

    emit(
        callback,
        "Researcher started",
    )

    for sub_question in (
        plan.sub_questions
    ):


        # 每个研究子问题使用独立 Tool Budget
        reset_search_count()
        reset_paper_search_count()

        emit(
            callback,
            (
                f"Researching sub-question "
                f"{sub_question.id}: "
                f"{sub_question.question}"
            ),
        )


        results = run_research_query(
            query=sub_question.question,

            search_type=(
                sub_question.search_type
            ),
        )


        evidence_store.add_many(
            results
        )


    state.evidence = evidence_store.get_all()


    state.status = (
        ResearchStatus.WRITING
    )


    # ======================
    # Step 3 Writer
    # ======================
    emit(
        callback,
        "Writer started",
    )


    evidence_json = json.dumps(
        [item.model_dump(mode="json") for item in state.evidence],
        ensure_ascii=False,
        indent=2,
    )

    writer_prompt = f"""
    请根据下面的研究问题和收集到的证据，
    生成结构化 Research Report。

    ====================
    研究问题
    ====================

    {question}


    ====================
    Evidence
    ====================

    {evidence_json}


    要求：

    1. 明确回答研究问题。
    2. 总结核心发现。
    3. 如果包含论文，请列出：
      - 标题
      - 作者
      - 年份
      - 引用量
      - 来源
    4. 不要编造不存在的信息。
    5. 输出完整研究报告。
    """


    report = run_writer(
        writer_prompt
    )


    state.draft_report = report


    # ======================
    # Step 4 Critic
    # ======================
    emit(
        callback,
        "Critic started",
    )
    
    state.status = ResearchStatus.REVIEWING

    review = run_critic(
        report
    )


    state.critic_review = review


    state.status = (
        ResearchStatus.COMPLETED
    )

    emit(
        callback,
        "Research completed",
    )

    return state
