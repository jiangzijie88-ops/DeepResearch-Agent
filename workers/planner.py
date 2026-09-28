from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from llm import get_model
from models.search_type import SearchType


class ResearchSubQuestion(BaseModel):
    id: int = Field(description="子问题编号")
    question: str = Field(description="需要调查的具体研究子问题")
    search_type: SearchType = Field(
        description="建议的检索类型，只能是 paper_search、web_search 或 hybrid"
    )


class ResearchPlan(BaseModel):
    research_goal: str = Field(description="本次研究任务的总体目标")
    sub_questions: list[ResearchSubQuestion] = Field(
        description="为了完成研究目标，需要依次解决的子问题"
    )


PLANNER_INSTRUCTIONS = """
你是 DeepResearch 系统中的 Planner Agent。

你的任务不是直接回答用户的问题，也不要自己搜索资料。

你的职责是：

1. 理解用户真正想研究的问题。
2. 将复杂研究问题拆分成若干明确、可执行的子问题。
3. 每个子问题应该可以交给后续 Researcher Agent 进行搜索。
4. 判断每个子问题适合使用：
   - paper_search：学术论文、作者、年份、引用量、DOI 等
   - web_search：网页资料、新闻、机构信息、行业资料等
   - hybrid：同时需要论文和网页信息
5. 子问题之间尽量减少重复。
6. 通常生成 3 到 6 个子问题。
7. 不要执行搜索。
8. 不要编造研究结果。

请使用 ResearchPlan 结构化输出返回研究目标和子问题，不要添加额外解释。

JSON 格式必须严格为：

OUTPUT FORMAT

必须只返回合法 JSON：

{
  "research_goal": "...",
  "sub_questions": [
    {
      "id": 1,
      "question": "...",
      "search_type": "paper_search"
    },
    {
      "id": 2,
      "question": "...",
      "search_type": "web_search"
    },
    {
      "id": 3,
      "question": "...",
      "search_type": "hybrid"
    }
  ]
}

search_type 只能是：
paper_search
web_search
hybrid


SEARCH TYPE RULES

每个研究子问题必须指定且只能指定以下一种 search_type：

1. "paper_search"
   用于需要检索学术论文、作者、发表年份、
   会议/期刊、DOI、引用量等学术元数据的问题。

2. "web_search"
   用于需要检索普通网页、新闻、官方网站、
   项目主页、公司信息、当前事件或其他非论文信息的问题。

3. "hybrid"
   仅当一个子问题确实同时需要学术论文信息
   和普通 Web 信息时使用。

禁止输出其他 search_type，例如：
"paper"、"papers"、"academic"、"google"、
"browser"、"search"、"academic_search"。


优先选择最小必要工具：

- 仅需要论文数据库信息时：
  使用 "paper_search"

- 仅需要公开网页信息时：
  使用 "web_search"

- 只有两类信息都必不可少时：
  才使用 "hybrid"

不要为了保险而默认使用 "hybrid"。
"""


planner_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=PLANNER_INSTRUCTIONS),
    ("human", """用户研究问题：
{question}

历史研究记忆：
{memory_context}

请基于用户问题和已有研究记忆生成新的 Research Plan。
如果历史记忆为空，不要假设已有知识。"""),
])


def create_planner_chain() -> Runnable[dict[str, str], ResearchPlan]:
    """Create Prompt -> Model -> Pydantic output lazily for each planning run."""
    return planner_prompt | get_model().with_structured_output(
        ResearchPlan, method="function_calling",
    )
