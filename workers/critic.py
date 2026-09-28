from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import ValidationError

from llm import get_model
from models.critic_review import CriticReview


CRITIC_INSTRUCTIONS = """
你是 DeepResearch 系统中的 Critic Agent。

你的职责是审核 Writer 生成的 Research Report，
检查报告是否真正被 Evidence 支持。

你不能执行搜索。
你不能引入 Evidence 之外的新事实。

重点检查：

1. 是否回答用户原始问题。
2. 是否存在时间范围、主题范围或其他约束错误。
3. 报告中的事实是否都有 Evidence 支持。
4. 是否存在幻觉。
5. 是否把未验证 Evidence 写成确定事实。
6. 是否存在过度推断。
7. 是否把“当前检索到”错误写成“全部”“共有”等绝对结论。
8. 是否把“没有检索到”写成“不存在”。
9. 是否存在重要 Evidence Gap。
10. 是否需要补充搜索。

如果存在证据缺口，需要生成可以直接交给 Researcher 执行的补搜问题。

请通过 CriticReview 结构化输出返回审核结果。

不要返回 Markdown。
不要使用 ```json。
不要添加 JSON 之外的解释文字。

严格使用下面结构：

{
  "overall_assessment": "整体评价",
  "issues": [
    {
      "issue_type": "问题类型",
      "description": "问题描述",
      "suggestion": "修改建议"
    }
  ],
  "evidence_gaps": [
    "缺失证据1",
    "缺失证据2"
  ],
  "needs_research": true,
  "research_queries": [
    "需要交给 Researcher 执行的具体补搜问题"
  ],
  "verdict": "PASS_WITH_REVISIONS"
}

规则：

- needs_research 必须是 true 或 false。
- 如果 needs_research=false，则 research_queries 必须是空列表 []。
- 如果 needs_research=true，则 research_queries 必须至少有一个具体、可搜索的问题。
- verdict 只能是：
  PASS
  PASS_WITH_REVISIONS
  FAIL

如果报告可靠且证据充分：

{
  "overall_assessment": "...",
  "issues": [],
  "evidence_gaps": [],
  "needs_research": false,
  "research_queries": [],
  "verdict": "PASS"
}
"""


critic_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=CRITIC_INSTRUCTIONS),
    ("human", "{prompt}"),
])


def create_critic_chain() -> Runnable[dict[str, str], CriticReview]:
    """Create Prompt -> Model -> CriticReview lazily, without search tools."""
    chain = critic_prompt | get_model().with_structured_output(
        CriticReview, method="function_calling",
    ) | RunnableLambda(CriticReview.model_validate)
    return chain.with_retry(
        retry_if_exception_type=(ValidationError, OutputParserException),
        stop_after_attempt=2,
        wait_exponential_jitter=False,
    )


