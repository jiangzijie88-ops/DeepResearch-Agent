from agents import Agent, Runner

from llm import get_model
from tools.web_search import (
    web_search,
    reset_search_count,
)
from tools.paper_search import (
    paper_search,
    reset_paper_search_count,
)
from skills.loader import load_skill


academic_search_skill = load_skill(
    "academic_search"
)

research_agent = Agent(
    name="Research Assistant",

    instructions=f"""
    You are a research assistant.

    Your job is to answer the user's research questions
    clearly and accurately.

    You have access to specialized skills.

    Follow the relevant skill instructions
    when the user's task matches that skill.

    =========================
    ACADEMIC SEARCH SKILL
    =========================

    {academic_search_skill}
    """,

    model=get_model(),

    tools=[
      web_search,
      paper_search,
    ]
)

question = input("请输入你的研究问题：\n")

reset_search_count()
reset_paper_search_count()

print("\n[Agent] Research Agent started.")
print(f"[User Question] {question}\n")

result = Runner.run_sync(
    research_agent,
    question,
    max_turns = 8
)


print("\n[Agent] Research Agent finished.")
print("\n" + "=" * 60)
print("FINAL ANSWER")
print("=" * 60)
print(result.final_output)