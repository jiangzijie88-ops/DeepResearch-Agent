import json
import os
import sys
from datetime import datetime


from tools.web_search import reset_search_count
from tools.paper_search import reset_paper_search_count

from models.evidence_store import EvidenceStore
from models.research_state import ResearchState, ResearchStatus
from models.state_store import save_state, load_state

from workflow.cli import parse_args
from workflow.resume import ResumeStage, get_resume_stage
from workflow.stages import (
    run_planner,
    run_writer,
    run_critic,
    run_research_query,
)
from memory.memory_item import (
    MemoryItem,
)

from memory.memory_storage import (
    save_memory,
    load_memory,
)

from memory.memory_context import (
    build_memory_context,
)


args = parse_args()

# ============================================================
# Workflow Log
# ============================================================

os.makedirs(
    "outputs",
    exist_ok=True,
)


timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)


log_path = os.path.join(
    "outputs",
    f"workflow_{timestamp}.log",
)

if args.resume:

    state_path = args.resume

else:

    state_path = os.path.join(
        "outputs",
        f"state_{timestamp}.json",
    )

log_file = open(
    log_path,
    "w",
    encoding="utf-8",
)


class Tee:

    def __init__(
        self,
        *streams,
    ):

        self.streams = streams


    def write(
        self,
        data,
    ):

        for stream in self.streams:

            stream.write(data)

            stream.flush()


    def flush(
        self,
    ):

        for stream in self.streams:

            stream.flush()


sys.stdout = Tee(
    sys.__stdout__,
    log_file,
)

sys.stderr = Tee(
    sys.__stderr__,
    log_file,
)


print(
    f"[Workflow] 完整日志将保存到：{log_path}"
)


# ============================================================
# User Question / Resume State
# ============================================================

if args.resume:

    state = load_state(
        state_path
    )

    question = state.question

    print(
        f"[Resume] 已加载 Research State："
        f"{state_path}"
    )

    print(
        f"[Resume] 当前 Workflow status: "
        f"{state.status.value}"
    )

    print(
        f"[Resume] Research round: "
        f"{state.research_round}"
    )

else:

    question = input(
        "请输入你的研究问题：\n"
    )

    state = ResearchState(
        question=question
    )

    save_state(
        state,
        state_path,
    )

resume_stage = get_resume_stage(
    state
)

print(
    f"[Workflow] Resume stage: "
    f"{resume_stage.value}"
)


if resume_stage == ResumeStage.DONE:

    print(
        "[Resume] 当前任务已经完成，"
        "无需重新执行 Workflow。"
    )

    if state.final_report:

        print("\n" + "=" * 60)
        print("FINAL REPORT")
        print("=" * 60)

        print(
            state.final_report
        )

    sys.exit(0)


# ============================================================
# Step 1: Planner
# ============================================================

if resume_stage == ResumeStage.PLANNER:

    print(
        "\n[Planner] 正在生成研究计划...\n"
    )

    memory_items = load_memory(
        "outputs/memory.json"
    )


    memory_context = build_memory_context(
        memory_items,
        state.question,
    )


    print(
        "\n[Memory] Planner 使用历史研究记忆:"
    )

    print(
        memory_context
    )


    plan = run_planner(
        state.question,
        memory_context=memory_context,
    )

    state.plan = plan
    state.status = ResearchStatus.PLANNED

    save_state(
        state,
        state_path,
    )

    resume_stage = get_resume_stage(
        state
    )

    print(
        f"[State] Workflow status: "
        f"{state.status.value}"
    )


else:

    plan = state.plan

    if plan is None:

        raise RuntimeError(
            "Resume state 显示 Planner 已完成，"
            "但 state.plan 为空。"
        )

    print(
        "[Resume] Planner 已完成，"
        "跳过 Planner 阶段。"
    )

print(
    f"[State] Workflow status: {state.status.value}"
)


print("\n" + "=" * 60)

print("RESEARCH PLAN")

print("=" * 60)


print(
    f"\n研究目标：{plan.research_goal}"
)


print("\n研究子问题：")


for sub_question in plan.sub_questions:

    print(
        f"{sub_question.id}. "
        f"{sub_question.question} "
        f"[{sub_question.search_type}]"
    )


# ============================================================
# Step 2: Researcher + Evidence Store
# ============================================================

evidence_store = EvidenceStore()


if resume_stage == ResumeStage.RESEARCH:

    state.status = ResearchStatus.RESEARCHING

    print(
        f"[State] Workflow status: "
        f"{state.status.value}"
    )


    for sub_question in plan.sub_questions:

        print("\n" + "=" * 60)

        print(
            f"[Researcher] 正在执行子问题 "
            f"{sub_question.id}"
        )

        print(
            f"[Task] {sub_question.question}"
        )

        print(
            f"[Suggested Search Type] "
            f"{sub_question.search_type}"
        )

        state.tool_routes[
            str(sub_question.id)
        ] = [
            sub_question.search_type.value
        ]

        print("=" * 60)


        # 每个子问题开始前重置 Tool Budget
        reset_search_count()
        reset_paper_search_count()


        try:

            evidence_list = run_research_query(
                query=sub_question.question,

                search_type=(
                    sub_question.search_type
                ),
)

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as e:

            print(
                f"\n[Evidence Parse Error] "
                f"子问题 {sub_question.id} "
                f"返回结果解析失败"
            )

            print(
                f"[Error] {e}"
            )

            print(
                "[Fallback] 本子问题按 0 条 Evidence 处理，"
                "Workflow 继续执行。"
            )

            evidence_list = []


        # 加入统一 Evidence Store
        added_count = evidence_store.add_many(
            evidence_list
        )


        print(
            f"\n[Evidence] 子问题 "
            f"{sub_question.id} "
            f"获得 {len(evidence_list)} 条证据，"
            f"新增 {added_count} 条，"
            f"当前总计 "
            f"{evidence_store.count()} 条"
        )


    state.evidence = evidence_store.get_all()

    save_state(
        state,
        state_path,
    )

    resume_stage = ResumeStage.WRITER

if resume_stage != ResumeStage.RESEARCH:

    evidence_store.add_many(
        state.evidence
    )


# ============================================================
# Step 3: Print Evidence Store
# ============================================================

state.evidence = evidence_store.get_all()

save_state(
    state,
    state_path,
)

print("\n\n" + "=" * 60)

print("FINAL EVIDENCE STORE")

print("=" * 60)


print(
    f"\n最终共收集 "
    f"{evidence_store.count()} 条去重 Evidence"
)


for index, evidence in enumerate(
    evidence_store.get_all(),
    start=1,
):

    print(
        f"\nEvidence {index}"
    )

    print(
        f"Title: {evidence.title}"
    )

    print(
        f"Authors: {', '.join(evidence.authors)}"
    )

    print(
        f"Venue: {evidence.venue}"
    )

    print(
        f"Published At: {evidence.published_at}"
    )

    print(
        f"Year: {evidence.year}"
    )

    print(
        f"Citations: {evidence.citations}"
    )

    print(
        f"Source: {evidence.source}"
    )

    print(
        f"Verified: {evidence.verified}"
    )

    print(
        "-" * 60
    )


# ============================================================
# Step 4: Serialize Evidence for Writer
# ============================================================

evidence_lines = []


for index, evidence in enumerate(
    evidence_store.get_all(),
    start=1,
):

    evidence_lines.append(
        f"""
    Evidence {index}

    Title: {evidence.title}
    Evidence Type: {evidence.evidence_type}
    Authors: {", ".join(evidence.authors)}
    Venue: {evidence.venue}
    Published At: {evidence.published_at}
    Year: {evidence.year}
    Citations: {evidence.citations}
    Source: {evidence.source}
    DOI: {evidence.doi}
    URL: {evidence.url}
    Summary: {evidence.summary}
    Query: {evidence.query}
    Retrieved At: {evidence.retrieved_at}
    Verified: {evidence.verified}
    Confidence: {evidence.confidence}
    """
    )


evidence_text = "\n".join(
    evidence_lines
)


# ============================================================
# Step 5: Writer
# ============================================================

if resume_stage == ResumeStage.WRITER:

    state.status = ResearchStatus.WRITING

    print(
        f"[State] Workflow status: "
        f"{state.status.value}"
    )

    writer_input = f"""
用户原始研究问题：

{question}


Research Goal:

{plan.research_goal}


以下是 Researcher 收集并经过 Evidence Store 去重后的证据。

你只能基于这些证据撰写报告。

不要执行搜索。
不要编造没有出现在 Evidence 中的事实。


{evidence_text}
"""

    print(
        "\n[Writer] 正在生成 Research Report...\n"
    )

    report_text = run_writer(
        writer_input
    )

    state.draft_report = report_text

    save_state(
        state,
        state_path,
    )

    resume_stage = ResumeStage.CRITIC


else:

    report_text = state.draft_report

    if report_text is None:

        raise RuntimeError(
            "Resume state 显示 Writer 已完成，"
            "但 state.draft_report 为空。"
        )

    print(
        "[Resume] Writer 第一版报告已完成，"
        "跳过 Writer 阶段。"
    )


# ============================================================
# Step 6: Final Report
# ============================================================

print("\n" + "=" * 60)

print("FINAL RESEARCH REPORT")

print("=" * 60)

print(
    report_text
)


# ============================================================
# Step 7: Critic
# ============================================================

if resume_stage == ResumeStage.CRITIC:

    critic_input = f"""
用户原始研究问题：

{question}


Research Goal:

{plan.research_goal}


下面是 Researcher 收集并经过 Evidence Store 去重后的证据：

{evidence_text}


下面是 Writer 生成的 Research Report：

{report_text}


请严格审核这份 Research Report。

重点检查：

1. 是否回答了用户原始问题。
2. 是否存在超出用户时间范围或主题范围的内容。
3. 每个重要事实是否有 Evidence 支持。
4. 是否把未验证 Evidence 当成确定事实。
5. 是否存在过度推断。
6. 是否把“当前检索到”错误写成“全部”“共有”等绝对结论。
7. 是否把“没有检索到”写成“不存在”。
8. 引用量、年份、论文信息是否和 Evidence 一致。
9. 是否需要补充搜索。

你只负责审核，不要重新搜索。
"""

    state.status = ResearchStatus.REVIEWING

    print(
        f"[State] Workflow status: "
        f"{state.status.value}"
    )

    print(
        "\n[Critic] 正在审核 Research Report...\n"
    )

    try:

        review = run_critic(
            critic_input
        )

        critic_raw_output = (
            review.model_dump_json(
                indent=2
            )
        )

        state.critic_review = review

        save_state(
            state,
            state_path,
        )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as e:

        print(
            "\n[Critic Parse Error] "
            "Critic 返回结果不是合法 JSON"
        )

        print(
            f"[Error] {e}"
        )

        review = None


else:

    review = state.critic_review

    if review is None:

        raise RuntimeError(
            "Resume state 显示 Critic 已完成，"
            "但 state.critic_review 为空。"
        )

    critic_raw_output = (
        review.model_dump_json(
            indent=2
        )
    )

    print(
        "[Resume] 第一轮 Critic 已完成，"
        "跳过 Critic 阶段。"
    )


if review is not None:

    print("\n" + "=" * 60)

    print("STRUCTURED CRITIC REVIEW")

    print("=" * 60)


    print(
        f"Verdict: {review.verdict}"
    )

    print(
        f"Needs Research: "
        f"{review.needs_research}"
    )


    print("\nResearch Queries:")

    for query in review.research_queries:

        print(
            f"- {query}"
        )

if (
    review is not None
    and review.needs_research
):
    resume_stage = ResumeStage.RE_RESEARCH

else:
    resume_stage = ResumeStage.REVISION


# ============================================================
# Step 8: Critic-Guided Additional Research
# ============================================================

if resume_stage == ResumeStage.RE_RESEARCH:

    state.status = ResearchStatus.RE_RESEARCHING
    state.research_round += 1

    print(
        f"[State] Workflow status: {state.status.value}"
    )

    print(
        f"[State] Research round: {state.research_round}"
    )

    print("\n" + "=" * 60)

    print("ADDITIONAL RESEARCH")

    print("=" * 60)


    # 一轮最多执行 3 个补搜任务
    for index, query in enumerate(
        review.research_queries[:3],
        start=1,
    ):

        print(
            f"\n[Re-Research] "
            f"正在执行补搜任务 {index}"
        )

        print(
            f"[Query] {query}"
        )


        # 每个补搜任务重新给 Tool Budget
        reset_search_count()
        reset_paper_search_count()


        try:

            additional_evidence = (
                run_research_query(
                    query
                )
            )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as e:

            print(
                f"[Re-Research Parse Error] "
                f"补搜任务 {index} "
                f"结果解析失败"
            )

            print(
                f"[Error] {e}"
            )

            additional_evidence = []


        added_count = evidence_store.add_many(
            additional_evidence
        )


        print(
            f"[Re-Research Evidence] "
            f"获得 "
            f"{len(additional_evidence)} 条，"
            f"新增 {added_count} 条，"
            f"Evidence Store 当前总计 "
            f"{evidence_store.count()} 条"
        )

if resume_stage == ResumeStage.RE_RESEARCH:

    state.evidence = (
        evidence_store.get_all()
    )

    state.status = (
        ResearchStatus.REVISING
    )

    save_state(
        state,
        state_path,
    )

    resume_stage = (
        ResumeStage.REVISION
    )


# ============================================================
# Step 9: Re-Serialize Updated Evidence
# ============================================================

updated_evidence_lines = []


for index, evidence in enumerate(
    evidence_store.get_all(),
    start=1,
):

    updated_evidence_lines.append(
        f"""
    Evidence {index}

    Title: {evidence.title}
    Evidence Type: {evidence.evidence_type}
    Authors: {", ".join(evidence.authors)}
    Venue: {evidence.venue}
    Published At: {evidence.published_at}
    Year: {evidence.year}
    Citations: {evidence.citations}
    Source: {evidence.source}
    DOI: {evidence.doi}
    URL: {evidence.url}
    Summary: {evidence.summary}
    Query: {evidence.query}
    Retrieved At: {evidence.retrieved_at}
    Verified: {evidence.verified}
    Confidence: {evidence.confidence}
    """
    )


updated_evidence_text = "\n".join(
    updated_evidence_lines
)


print(
    f"\n[Workflow] 补搜完成后 Evidence Store "
    f"共 {evidence_store.count()} 条证据"
)


# ============================================================
# Step 10: Writer Revision
# ============================================================

if resume_stage == ResumeStage.REVISION:

    state.status = ResearchStatus.REVISING

    print(
        f"[State] Workflow status: "
        f"{state.status.value}"
    )

    revision_input = f"""
用户原始研究问题：

{question}


Research Goal:

{plan.research_goal}


下面是补充搜索完成后的最新 Evidence Store：

{updated_evidence_text}


下面是 Writer 第一版 Research Report：

{report_text}


下面是 Critic 第一轮审核结果：

{critic_raw_output}


请基于最新 Evidence 对报告进行修订。

要求：

1. 必须优先解决 Critic 指出的问题。
2. 必须使用新增 Evidence 补充原报告。
3. 不要保留已经被 Critic 判定为证据不足的绝对化表述。
4. 不要编造 Evidence 中不存在的信息。
5. verified=false 的信息必须谨慎表述。
6. 如果补搜仍然没有解决某些问题，应明确说明证据仍然不足。
7. 输出完整、可直接交付给用户的最终研究报告。
"""

    print(
        "\n[Writer] 正在基于最新 Evidence 修订报告...\n"
    )

    revised_report_text = run_writer(
        revision_input
    )

    state.final_report = (
        revised_report_text
    )

    state.status = (
        ResearchStatus.FINAL_REVIEWING
    )

    save_state(
        state,
        state_path,
    )

    resume_stage = (
        ResumeStage.FINAL_CRITIC
    )


else:

    revised_report_text = (
        state.final_report
    )

    if revised_report_text is None:

        raise RuntimeError(
            "Resume state 显示 Revision 已完成，"
            "但 state.final_report 为空。"
        )

    print(
        "[Resume] Writer Revision 已完成，"
        "跳过 Revision 阶段。"
    )

# ============================================================
# Step 11: Final Critic Review
# ============================================================

if resume_stage == ResumeStage.FINAL_CRITIC:

    state.status = (
        ResearchStatus.FINAL_REVIEWING
    )

    print(
        f"[State] Workflow status: "
        f"{state.status.value}"
    )

    final_critic_input = f"""
用户原始研究问题：

{question}


Research Goal:

{plan.research_goal}


最新 Evidence Store：

{updated_evidence_text}


下面是 Writer 修订后的 Research Report：

{revised_report_text}


请进行最终审核。

重点检查：

1. 第一轮 Critic 指出的问题是否已修复。
2. 新增 Evidence 是否被正确使用。
3. 是否仍有事实错误。
4. 是否仍有时间范围或主题范围错误。
5. 是否仍有未经 Evidence 支持的结论。
6. 是否仍存在过度推断。
7. 是否已经足以作为 Final Report。
8. 如果仍有证据缺口，请如实记录。

必须严格按照 Critic JSON Schema 输出。
"""

    print(
        "\n[Critic] 正在进行第二次最终审核...\n"
    )

    try:

        final_review = run_critic(
            final_critic_input
        )

        state.final_review = (
            final_review
        )

        save_state(
            state,
            state_path,
        )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as e:

        print(
            "\n[Final Critic Parse Error] "
            "第二次 Critic 输出解析失败"
        )

        print(
            f"[Error] {e}"
        )

        final_review = None


else:

    final_review = (
        state.final_review
    )

    print(
        "[Resume] Final Critic 已完成，"
        "跳过最终审核阶段。"
    )


# ============================================================
# Step 12: Final Output
# ============================================================

print("\n" + "=" * 60)

print("FINAL REPORT")

print("=" * 60)

print(
    revised_report_text
)



if final_review is not None:

    print("\n" + "=" * 60)

    print("FINAL CRITIC RESULT")

    print("=" * 60)

    print(
        f"Verdict: {final_review.verdict}"
    )

    print(
        f"Needs Research: "
        f"{final_review.needs_research}"
    )


    if final_review.evidence_gaps:

        print("\nRemaining Evidence Gaps:")

        for gap in final_review.evidence_gaps:

            print(
                f"- {gap}"
            )



            
# ============================================================
# Save Final Report
# ============================================================

report_path = os.path.join(
    "outputs",
    f"report_{timestamp}.md",
)


with open(
    report_path,
    "w",
    encoding="utf-8",
) as report_file:

    report_file.write(
        revised_report_text
    )


print(
    f"\n[Workflow] 最终研究报告已保存到："
    f"{report_path}"
)


# ============================================================
# Save Final Critic Review
# ============================================================

if final_review is not None:

    critic_path = os.path.join(
        "outputs",
        f"critic_{timestamp}.json",
    )

    with open(
        critic_path,
        "w",
        encoding="utf-8",
    ) as critic_file:

        json.dump(
            final_review.model_dump(),
            critic_file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"[Workflow] 最终审核结果已保存到："
        f"{critic_path}"
    )


memory_path = os.path.join(
    "outputs",
    "memory.json",
)


memory_items = load_memory(
    memory_path
)


memory_items.append(
    MemoryItem(
        question=question,

        summary=(
            revised_report_text[:500]
        ),

        evidence_count=(
            evidence_store.count()
        ),
    )
)


save_memory(
    memory_items,
    memory_path,
)


print(
    f"[Memory] 已保存研究经验，"
    f"当前 Memory 数量："
    f"{len(memory_items)}"
)


state.status = ResearchStatus.COMPLETED

resume_stage = ResumeStage.DONE

save_state(
    state,
    state_path,
)

print(
    f"[State] Workflow status: {state.status.value}"
)

print(
    f"[Workflow] Research State 已保存到：{state_path}"
)
