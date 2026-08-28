from pydantic import BaseModel, Field
from agents import Agent

from llm import get_model


class ResearchSubQuestion(BaseModel):
    id: int = Field(description="子问题编号")
    question: str = Field(description="需要调查的具体研究子问题")
    search_type: str = Field(
        description="建议的检索类型，只能是 paper_search、web_search 或 both"
    )


class ResearchPlan(BaseModel):
    research_goal: str = Field(description="本次研究任务的总体目标")
    sub_questions: list[ResearchSubQuestion] = Field(
        description="为了完成研究目标，需要依次解决的子问题"
    )


planner_agent = Agent(
    name="Research Planner",

    instructions="""
你是 DeepResearch 系统中的 Planner Agent。

你的任务不是直接回答用户的问题，也不要自己搜索资料。

你的职责是：

1. 理解用户真正想研究的问题。
2. 将复杂研究问题拆分成若干明确、可执行的子问题。
3. 每个子问题应该可以交给后续 Researcher Agent 进行搜索。
4. 判断每个子问题适合使用：
   - paper_search：学术论文、作者、年份、引用量、DOI 等
   - web_search：网页资料、新闻、机构信息、行业资料等
   - both：同时需要论文和网页信息
5. 子问题之间尽量减少重复。
6. 通常生成 3 到 6 个子问题。
7. 不要执行搜索。
8. 不要编造研究结果。

你必须只返回合法 JSON，不要输出 Markdown，不要输出 ```json，
不要添加解释文字。

JSON 格式必须严格为：

{
  "research_goal": "研究总体目标",
  "sub_questions": [
    {
      "id": 1,
      "question": "具体研究子问题",
      "search_type": "paper_search"
    }
  ]
}

search_type 只能是：
paper_search
web_search
both
""",

    model=get_model(),
)