import json
import logging
from pathlib import Path
from openai import APIConnectionError


logger = logging.getLogger(__name__)

from memory import (
    MemoryItem,
    build_memory_context,
    load_memory,
    save_memory,
)

from models.evidence_store import EvidenceStore
from models.research_state import (
    ResearchState,
    ResearchStatus,
)
from models.state_store import save_state
from workflow.events import EventSink, emit_event, workflow_lifecycle
from workflow.citations import append_references, report_body
from workflow.citation_validation import (
    validate_citations, build_support_context, merge_citation_review,
)

from tools.paper_search import (
    reset_paper_search_count,
)
from tools.web_search import (
    reset_search_count,
)

from workflow.resume import (
    ResumeStage,
    get_resume_stage,
)
from workflow.stages import (
    run_critic,
    run_planner,
    run_research_query,
    run_writer,
)


def emit(
    callback,
    message: str,
) -> None:
    """
    向 API / Streamlit 等调用方发送 Workflow 事件。
    """

    if callback:
        callback(message)


def checkpoint(
    state: ResearchState,
    state_path: str | Path | None,
) -> None:
    """
    如果提供 checkpoint 路径，
    保存当前 ResearchState。
    """

    if state_path:
        save_state(
            state,
            state_path,
        )


def serialize_evidence(
    evidence_list,
) -> str:
    """
    将 Evidence 序列化为 JSON，
    供 Writer 和 Critic 使用。
    """

    data = []

    for evidence in evidence_list:
        data.append(
            dict(evidence.model_dump(), citation=f"[{evidence.evidence_id}]" if evidence.evidence_id else None)
        )

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def run_research_tasks(
    plan,
    evidence_store: EvidenceStore,
    state: ResearchState,
    on_event: EventSink | None = None,
) -> None:
    """
    执行 Planner 生成的所有研究子问题。
    """

    state.status = (
        ResearchStatus.RESEARCHING
    )

    for sub_question in (
        plan.sub_questions
    ):

        emit_event(on_event, "progress", "researcher", "正在检索子问题",
                   subquestion_id=sub_question.id, search_type=sub_question.search_type.value)

        state.tool_routes[
            str(sub_question.id)
        ] = [
            sub_question.search_type.value
        ]

        # 每一个任务拥有独立 Tool Budget
        reset_search_count()
        reset_paper_search_count()

        try:

            evidence_list = (
                run_research_query(
                    query=(
                        sub_question.question
                    ),
                    search_type=(
                        sub_question.search_type
                    ),
                )
            )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:

            print(
                f"[Evidence Parse Error] "
                f"子问题 {sub_question.id} "
                f"返回结果解析失败: {exc}"
            )

            evidence_list = []

        added = evidence_store.add_many(
            evidence_list
        )
        emit_event(on_event, "progress", "researcher", "已收集研究证据",
                   evidence_count=evidence_store.count(), new_evidence_count=added)

    state.evidence = (
        evidence_store.get_all()
    )


def run_additional_research(
    review,
    evidence_store: EvidenceStore,
    state: ResearchState,
    on_event: EventSink | None = None,
) -> None:
    """
    根据 Critic 给出的 research_queries
    执行补充搜索。
    """

    state.status = (
        ResearchStatus.RE_RESEARCHING
    )

    state.research_round += 1

    # 一轮最多补搜 3 个问题
    for query in (
        review.research_queries[:3]
    ):

        reset_search_count()
        reset_paper_search_count()

        try:

            evidence_list = (
                run_research_query(
                    query
                )
            )

        except APIConnectionError as exc:
            emit_event(on_event, "warning", "re_research", "补充研究连接失败，保留已有证据")
            # SDK retries have already been exhausted. Preserve collected
            # evidence and let revision address the outstanding critic gaps.
            logger.warning(
                "Additional research model connection failed (%s); "
                "continuing with existing evidence.",
                type(exc).__name__,
            )
            evidence_list = []

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:

            print(
                "[Re-Research Parse Error] "
                f"{exc}"
            )

            evidence_list = []

        evidence_store.add_many(
            evidence_list
        )

    state.evidence = (
        evidence_store.get_all()
    )


@workflow_lifecycle
def run_research_pipeline(
    question: str | None = None,
    callback=None,
    *,
    state: ResearchState | None = None,
    state_path: str | Path | None = None,
    memory_path: str | Path | None = None,
    on_event: EventSink | None = None,
) -> ResearchState:
    """
    DeepResearch 完整 Workflow。

    支持：
    - 新任务
    - Resume
    - Planner
    - Researcher
    - Evidence Store
    - Writer
    - Critic
    - Critic-guided re-research
    - Revision
    - Final Critic
    - Memory
    - Checkpoint
    """

    # ========================================================
    # Initialize / Resume
    # ========================================================

    if state is None:

        if not question:

            raise ValueError(
                "question 不能为空"
            )

        state = ResearchState(
            question=question
        )

    else:

        question = state.question

    resume_stage = (
        get_resume_stage(
            state
        )
    )

    if (
        resume_stage
        == ResumeStage.DONE
    ):
        return state

    # ========================================================
    # 1. Planner
    # ========================================================

    if (
        resume_stage
        == ResumeStage.PLANNER
    ):

        emit(
            callback,
            "Planner started",
        )

        emit_event(on_event, "stage_started", "planner", "正在生成研究计划")
        memory_context = ""

        if memory_path:

            memory_context = (
                build_memory_context(
                    load_memory(
                        memory_path
                    ),
                    state.question,
                )
            )

        if memory_context:

            state.plan = run_planner(
                state.question,
                memory_context=(
                    memory_context
                ),
            )

        else:

            state.plan = run_planner(
                state.question
            )

        emit_event(on_event, "stage_completed", "planner", "研究计划生成完成",
                   subquestion_count=len(state.plan.sub_questions))
        state.status = (
            ResearchStatus.PLANNED
        )

        checkpoint(
            state,
            state_path,
        )

        resume_stage = (
            ResumeStage.RESEARCH
        )

    plan = state.plan

    if plan is None:

        raise RuntimeError(
            "state.plan 为空，"
            "无法继续 Workflow"
        )

    # ========================================================
    # Evidence Store
    # ========================================================

    evidence_store = (
        EvidenceStore()
    )

    # Resume 时恢复旧证据
    evidence_store.add_many(
        state.evidence
    )

    # ========================================================
    # 2. Research
    # ========================================================

    if (
        resume_stage
        == ResumeStage.RESEARCH
    ):

        emit(
            callback,
            "Researcher started",
        )

        for sub_question in (
            plan.sub_questions
        ):

            emit(
                callback,
                (
                    "Researching "
                    f"sub-question "
                    f"{sub_question.id}: "
                    f"{sub_question.question}"
                ),
            )

        emit_event(on_event, "stage_started", "researcher", "正在检索研究证据")
        run_research_tasks(
            plan,
            evidence_store,
            state,
            on_event=on_event,
        )
        emit_event(on_event, "stage_completed", "researcher", "研究证据检索完成",
                   evidence_count=evidence_store.count())

        checkpoint(
            state,
            state_path,
        )

        resume_stage = (
            ResumeStage.WRITER
        )

    state.evidence = (
        evidence_store.get_all()
    )

    evidence_text = (
        serialize_evidence(
            state.evidence
        )
    )

    # ========================================================
    # 3. Writer
    # ========================================================

    if (
        resume_stage
        == ResumeStage.WRITER
    ):

        emit(
            callback,
            "Writer started",
        )

        state.status = (
            ResearchStatus.WRITING
        )

        writer_input = f"""
用户原始研究问题：

{state.question}


Research Goal：

{plan.research_goal}


以下是 Researcher 收集并经过
Evidence Store 去重后的证据。

你只能基于这些证据撰写报告。

不要执行搜索。
不要编造 Evidence 中不存在的事实。


{evidence_text}
"""

        emit_event(on_event, "stage_started", "writer", "正在撰写报告初稿")
        state.draft_report = (
            run_writer(
                writer_input
            )
        )
        state.draft_report = append_references(state.draft_report, state.evidence)
        emit_event(on_event, "stage_completed", "writer", "报告初稿撰写完成")

        checkpoint(
            state,
            state_path,
        )

        resume_stage = (
            ResumeStage.CRITIC
        )

    report_text = (
        state.draft_report
    )

    if report_text is None:

        raise RuntimeError(
            "state.draft_report 为空，"
            "无法继续 Workflow"
        )

    # ========================================================
    # 4. Critic
    # ========================================================

    review = (
        state.critic_review
    )

    if (
        resume_stage
        == ResumeStage.CRITIC
    ):
        emit_event(on_event, "stage_started", "citation_validation", "正在校验报告引用")
        validation = validate_citations(report_text, state.evidence)
        emit_event(on_event, "stage_completed", "citation_validation", "报告引用校验完成",
                   citation_count=validation.citation_count, invalid_citation_count=len(validation.invalid_citation_ids))
        support_context = json.dumps(
            build_support_context(validation, state.evidence), ensure_ascii=False, indent=2,
        )
        critic_body = report_body(report_text)

        emit(
            callback,
            "Critic started",
        )

        state.status = (
            ResearchStatus.REVIEWING
        )

        critic_input = f"""
用户原始研究问题：

{state.question}


Research Goal：

{plan.research_goal}


Evidence / Citation Support Batch：

{support_context}


Research Report：

{critic_body}


请严格审核这份 Research Report。

重点检查：

1. 是否回答用户的问题。
2. 是否超出时间范围或主题范围。
3. 重要事实是否有 Evidence 支持。
4. 是否使用未验证 Evidence 作为确定事实。
5. 是否存在过度推断。
6. 是否把“当前检索到”写成“全部”。
7. 是否把“没有检索到”写成“不存在”。
8. 论文信息是否与 Evidence 一致。
9. 是否需要补充搜索。

你只负责审核，不要搜索。
"""

        emit_event(on_event, "stage_started", "critic", "正在审查报告质量")
        try:

            review = run_critic(
                critic_input
            )
            review = merge_citation_review(review, validation)

            state.critic_review = (
                review
            )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:

            print(
                "[Critic Parse Error] "
                f"{exc}"
            )

            review = None

        emit_event(on_event, "stage_completed", "critic", "报告质量审查完成",
                   needs_research=bool(review and review.needs_research))
        if review and review.needs_research:
            emit_event(on_event, "warning", "critic", "发现研究缺口")

        checkpoint(
            state,
            state_path,
        )

    if (
        review is not None
        and review.needs_research
    ):

        resume_stage = (
            ResumeStage.RE_RESEARCH
        )

    else:

        resume_stage = (
            ResumeStage.REVISION
        )

    # ========================================================
    # 5. Additional Research
    # ========================================================

    if (
        resume_stage
        == ResumeStage.RE_RESEARCH
    ):

        emit_event(on_event, "stage_started", "re_research", "正在根据研究缺口补充检索")
        previous_count = evidence_store.count()
        run_additional_research(
            review,
            evidence_store,
            state,
            on_event=on_event,
        )
        emit_event(on_event, "stage_completed", "re_research", "补充研究完成",
                   new_evidence_count=evidence_store.count() - previous_count)

        state.status = (
            ResearchStatus.REVISING
        )

        checkpoint(
            state,
            state_path,
        )

        resume_stage = (
            ResumeStage.REVISION
        )

    state.evidence = (
        evidence_store.get_all()
    )

    updated_evidence_text = (
        serialize_evidence(
            state.evidence
        )
    )

    critic_raw_output = (
        review.model_dump_json(
            indent=2
        )
        if review is not None
        else "{}"
    )

    # ========================================================
    # 6. Writer Revision
    # ========================================================

    if (
        resume_stage
        == ResumeStage.REVISION
    ):

        state.status = (
            ResearchStatus.REVISING
        )

        revision_input = f"""
用户原始研究问题：

{state.question}


Research Goal：

{plan.research_goal}


最新 Evidence Store：

{updated_evidence_text}


Writer 第一版 Research Report：

{report_text}


Critic 第一轮审核：

{critic_raw_output}


请基于最新 Evidence 修订报告。

要求：

1. 优先解决 Critic 指出的问题。
2. 使用新增 Evidence。
3. 不要编造 Evidence 中不存在的信息。
4. verified=false 的内容谨慎表述。
5. 如果证据仍不足，应明确说明。
6. 输出完整最终研究报告。
"""

        emit_event(on_event, "stage_started", "revision", "正在修订研究报告")
        state.final_report = (
            run_writer(
                revision_input
            )
        )
        state.final_report = append_references(state.final_report, state.evidence)
        emit_event(on_event, "stage_completed", "revision", "研究报告修订完成")

        state.status = (
            ResearchStatus.FINAL_REVIEWING
        )

        checkpoint(
            state,
            state_path,
        )

        resume_stage = (
            ResumeStage.FINAL_CRITIC
        )

    final_report = (
        state.final_report
    )

    if final_report is None:

        raise RuntimeError(
            "state.final_report 为空，"
            "无法继续 Workflow"
        )

    # ========================================================
    # 7. Final Critic
    # ========================================================

    if (
        resume_stage
        == ResumeStage.FINAL_CRITIC
    ):
        emit_event(on_event, "stage_started", "citation_validation", "正在校验修订报告引用")
        final_validation = validate_citations(final_report, state.evidence)
        emit_event(on_event, "stage_completed", "citation_validation", "修订报告引用校验完成",
                   citation_count=final_validation.citation_count, invalid_citation_count=len(final_validation.invalid_citation_ids))
        final_support_context = json.dumps(
            build_support_context(final_validation, state.evidence), ensure_ascii=False, indent=2,
        )
        final_critic_body = report_body(final_report)

        final_critic_input = f"""
用户原始研究问题：

{state.question}


Research Goal：

{plan.research_goal}


Evidence / Citation Support Batch：

{final_support_context}


Writer 修订后的 Research Report：

{final_critic_body}


请进行最终审核。

重点检查：

1. 第一轮 Critic 的问题是否已解决。
2. Evidence 是否被正确使用。
3. 是否仍有事实错误。
4. 是否超出研究范围。
5. 是否存在无证据结论。
6. 是否存在过度推断。
7. 是否仍有 Evidence Gap。

必须按照 Critic JSON Schema 输出。
"""

        emit_event(on_event, "stage_started", "final_critic", "正在进行最终审查")
        try:

            state.final_review = (
                run_critic(
                    final_critic_input
                )
            )
            state.final_review = merge_citation_review(state.final_review, final_validation)

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:

            print(
                "[Final Critic Parse Error] "
                f"{exc}"
            )

            state.final_review = None
        emit_event(on_event, "stage_completed", "final_critic", "最终审查完成")

    # ========================================================
    # Complete
    # ========================================================

    state.status = (
        ResearchStatus.COMPLETED
    )

    checkpoint(
        state,
        state_path,
    )

    # ========================================================
    # Memory
    # ========================================================

    if memory_path:

        memory_items = (
            load_memory(
                memory_path
            )
        )

        memory_items.append(
            MemoryItem(
                question=(
                    state.question
                ),
                summary=(
                    final_report[:500]
                ),
                evidence_count=(
                    len(state.evidence)
                ),
            )
        )

        save_memory(
            memory_items,
            memory_path,
        )

    emit(
        callback,
        "Research completed",
    )

    return state


def save_run_outputs(
    state: ResearchState,
    output_dir: str | Path,
    timestamp: str,
) -> tuple[
    Path,
    Path | None,
]:
    """
    保存最终 Report 和 Critic Review。
    """

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        output_dir
        / f"report_{timestamp}.md"
    )

    report_path.write_text(
        state.final_report or "",
        encoding="utf-8",
    )

    critic_path = None

    if (
        state.final_review
        is not None
    ):

        critic_path = (
            output_dir
            / f"critic_{timestamp}.json"
        )

        critic_path.write_text(
            json.dumps(
                state.final_review.model_dump(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return (
        report_path,
        critic_path,
    )
