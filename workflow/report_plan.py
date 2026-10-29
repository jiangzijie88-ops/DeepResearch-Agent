"""Add the original Planner questions to the report without model rewriting."""

import re

from workers.planner import ResearchPlan


def include_research_questions(report: str, plan: ResearchPlan | None) -> str:
    """Replace the reserved section and insert it after the research question."""
    if plan is None or not plan.sub_questions:
        return report
    body = re.sub(
        r"^##[ \t]+研究子问题[ \t]*\r?$.*?(?=^#{1,2}[ \t]|\Z)",
        "", report, flags=re.MULTILINE | re.DOTALL,
    )
    questions = []
    for number, item in enumerate(plan.sub_questions, 1):
        # Indentation preserves multiline questions within the same list item.
        question = item.question.replace("\n", "\n   ")
        questions.append(f"{number}. {question}")
    section = "## 研究子问题\n\n" + "\n".join(questions)
    question_heading = re.search(
        r"^##[ \t]+(?:研究问题|Research Question)[ \t]*\r?$",
        body, flags=re.MULTILINE | re.IGNORECASE,
    )
    if question_heading:
        next_heading = re.search(r"^#{1,2}[ \t]", body[question_heading.end():], re.MULTILINE)
        position = question_heading.end() + next_heading.start() if next_heading else len(body)
    else:
        title = re.match(r"^#[ \t]+[^\n]*(?:\n|$)", body)
        position = title.end() if title else 0
    before, after = body[:position].rstrip(), body[position:].lstrip()
    return "\n\n".join(part for part in (before, section, after) if part)
