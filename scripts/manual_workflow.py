import json
import os
import sys
from datetime import datetime

from agents import Runner

from workers.planner import planner_agent, ResearchPlan
from workers.researcher import researcher_agent
from workers.writer import writer_agent
from workers.critic import critic_agent

from tools.web_search import reset_search_count
from tools.paper_search import reset_paper_search_count

from models.evidence import Evidence
from models.evidence_store import EvidenceStore
from models.critic_review import CriticReview


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
# User Question
# ============================================================

question = input("请输入你的研究问题：\n")


# ============================================================
# Step 1: Planner
# ============================================================

print("\n[Planner] 正在生成研究计划...\n")


planner_result = Runner.run_sync(
    planner_agent,
    question,
    max_turns=3,
)


raw_plan = planner_result.final_output


# JSON String -> Python dict
plan_dict = json.loads(raw_plan)


# dict -> ResearchPlan
plan = ResearchPlan.model_validate(
    plan_dict
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

    print("=" * 60)


    # 每个子问题开始前重置 Tool Budget
    reset_search_count()
    reset_paper_search_count()


    researcher_result = Runner.run_sync(
        researcher_agent,
        sub_question.question,
        max_turns=8,
    )


    raw_output = researcher_result.final_output


    # ============================================================
    # Safe Parse Researcher Output
    # ============================================================

    try:

        data = json.loads(
            raw_output
        )

        evidence_list = [
            Evidence.model_validate(item)
            for item in data.get(
                "evidence",
                []
            )
        ]


    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as e:

        print(
            f"\n[Evidence Parse Error] "
            f"子问题 {sub_question.id} "
            f"返回结果不是合法 JSON"
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


# ============================================================
# Step 3: Print Evidence Store
# ============================================================

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
Year: {evidence.year}
Citations: {evidence.citations}
Source: {evidence.source}
DOI: {evidence.doi}
URL: {evidence.url}
Summary: {evidence.summary}
Verified: {evidence.verified}
"""
    )


evidence_text = "\n".join(
    evidence_lines
)


# ============================================================
# Step 5: Writer
# ============================================================

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


writer_result = Runner.run_sync(
    writer_agent,
    writer_input,
    max_turns=3,
)


# ============================================================
# Step 6: Final Report
# ============================================================

print("\n" + "=" * 60)

print("FINAL RESEARCH REPORT")

print("=" * 60)


print(
    writer_result.final_output
)



# ============================================================
# Step 7: Critic
# ============================================================

report_text = writer_result.final_output


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


print(
    "\n[Critic] 正在审核 Research Report...\n"
)


critic_result = Runner.run_sync(
    critic_agent,
    critic_input,
    max_turns=3,
)
critic_raw_output = critic_result.final_output


try:

    critic_data = json.loads(
        critic_raw_output
    )

    review = CriticReview.model_validate(
        critic_data
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


# ============================================================
# Step 8: Critic-Guided Additional Research
# ============================================================

if (
    review is not None
    and review.needs_research
):

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


        additional_result = Runner.run_sync(
            researcher_agent,
            query,
            max_turns=8,
        )


        raw_output = (
            additional_result.final_output
        )


        try:

            data = json.loads(
                raw_output
            )

            additional_evidence = [
                Evidence.model_validate(item)
                for item in data.get(
                    "evidence",
                    []
                )
            ]


        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as e:

            print(
                f"[Re-Research Parse Error] "
                f"补搜任务 {index} "
                f"结果不是合法 JSON"
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
Year: {evidence.year}
Citations: {evidence.citations}
Source: {evidence.source}
DOI: {evidence.doi}
URL: {evidence.url}
Summary: {evidence.summary}
Verified: {evidence.verified}
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
    "\n[Writer] 正在基于补搜 Evidence 重写报告...\n"
)


revised_writer_result = Runner.run_sync(
    writer_agent,
    revision_input,
    max_turns=3,
)


revised_report_text = (
    revised_writer_result.final_output
)


# ============================================================
# Step 11: Final Critic Review
# ============================================================

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


final_critic_result = Runner.run_sync(
    critic_agent,
    final_critic_input,
    max_turns=3,
)


final_critic_raw = (
    final_critic_result.final_output
)


try:

    final_critic_data = json.loads(
        final_critic_raw
    )

    final_review = CriticReview.model_validate(
        final_critic_data
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



# ============================================================
# Step 12: Final Output
# ============================================================

print("\n" + "=" * 60)

print("FINAL REPORT")

print("=" * 60)

print(
    revised_report_text
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
