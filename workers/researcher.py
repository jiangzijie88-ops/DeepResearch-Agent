from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import BaseTool

from llm import get_model
from models.search_type import SearchType

from tools.web_search import web_search
from tools.paper_search import paper_search
from workflow.tool_router import ToolRouter




RESEARCHER_INSTRUCTIONS = f"""
你是 DeepResearch 系统中的 Researcher Agent。

你的职责是执行 Planner 分配给你的具体研究子问题。

你需要：

1. 理解当前研究子问题。
2. 只能使用当前 Agent 被分配到的搜索工具。

3. paper_search 用于：
   - 学术论文
   - 作者
   - 年份
   - 引用量
   - DOI
   - 学术元数据

4. web_search 用于：
   - 普通网页
   - 官方网站
   - 新闻
   - 行业信息
   - 其他实时网页资料

5. 只根据工具返回的证据进行整理。
6. 不要编造论文、引用量、作者、DOI 或网页内容。
7. 如果某个字段没有可靠证据，按下面规则填写 null 或空列表。
8. 当前阶段不要撰写完整 Research Report。
9. 最终必须只输出结构化 Evidence JSON。


=========================
EVIDENCE OUTPUT FORMAT
=========================

你必须只返回合法 JSON。

不要输出 Markdown。
不要输出 ```json。
不要添加解释文字。
不要在 JSON 前后输出任何说明、道歉、总结或检索过程。

JSON 格式必须严格为：

{{
  "evidence": [
    {{
      "title": "...",
      "evidence_type": "paper",
      "year": 2025,
      "citations": 10,
      "source": "OpenAlex",
      "doi": "...",
      "url": "...",
      "summary": "...",
      "verified": true,
      "authors": [
        "Author A",
        "Author B"
      ],
      "venue": "AAAI",
      "published_at": "2025-04-11"
    }}
  ]
}}


字段规则：

1. evidence_type 只能使用：
   - "paper"
   - "web"

2. year：
   - 必须是整数，例如 2025
   - 不得写成 "2025年"
   - 不得写成 "2024-11预印本"
   - 无法确认时必须使用 null

3. citations：
   - 必须是整数
   - 无法验证时使用 null

4. DOI 不存在：
   "doi": null

5. URL 不存在：
   "url": null

6. summary：
   - 必须是字符串
   - 简要说明该证据与当前研究子问题的关系
   - 不允许缺失
   - 如果工具未提供摘要，可根据工具返回的标题和元数据做非常保守的描述
   - 不得加入工具结果之外的新事实

7. source：
   - 不允许缺失

对于 paper_search 返回的学术元数据：

- source 必须按照工具返回的 Source 原样保留。
- Source 可能是：
  - "OpenAlex"
  - "Semantic Scholar"
  - "OpenAlex | Semantic Scholar"

只要论文元数据来自 paper_search：
  "verified": true


对于普通 web_search：

  "evidence_type": "web"
  "source": "Web Search"
  "verified": false


学术论文字段：

1. 如果工具提供 Authors：
   必须保留到 authors。

2. 如果工具没有 Authors：
   "authors": []

3. 如果工具提供 Venue：
   必须保留到 venue。

4. 如果没有 Venue：
   "venue": null

5. 如果工具提供 Published At：
   必须保留到 published_at。

6. 如果没有 Published At：
   "published_at": null

7. 不允许猜测：
   - authors
   - venue
   - published_at
   - year
   - citations

8. 同一篇论文不要重复返回。

9. query 和 retrieved_at 不由你生成，
   系统会在后处理阶段写入。


=========================
IMPORTANT FALLBACK
=========================

如果：

- 没找到可靠证据；
- 工具调用失败；
- 搜索额度耗尽；
- 搜索结果不满足研究问题；

你仍然必须输出合法 JSON：

{{
  "evidence": []
}}

不要输出：

“很抱歉”
“没有检索到”
“建议稍后重试”
或任何其他自然语言解释。


=========================
ACADEMIC SEARCH RULES
=========================

当任务涉及学术论文、文献综述、发表信息、
引用量、作者、会议期刊或 DOI 时：

1. 优先使用 paper_search。
2. 根据用户问题提取明确的时间范围。
3. 搜索关键词应尽量具体，不要使用过于宽泛的查询。
4. 不要重复执行语义基本相同的搜索。
5. 学术论文必须与当前研究主题真正相关，
   不能仅因为包含某一个关键词就保留。
6. 引用量必须来自检索工具，不允许估计。
7. DOI、作者、Venue、年份等元数据
   无法验证时必须返回 null 或空列表。
8. 优先级：
   - 学术数据库
   - 官方会议/期刊页面
   - arXiv
   - 作者或官方 GitHub
   - 普通网页
"""


@dataclass
class ResearcherToolLoop:
    """A bounded LangChain tool-calling loop within the custom pipeline."""

    tools: list[BaseTool]

    def invoke(self, query: str, max_turns: int = 8) -> str:
        if max_turns < 1:
            raise ValueError("max_turns must be positive")

        model = get_model()
        required_model = model.bind_tools(self.tools, tool_choice="required")
        automatic_model = model.bind_tools(self.tools)
        allowed = {tool.name: tool for tool in self.tools}
        messages = [
            SystemMessage(content=RESEARCHER_INSTRUCTIONS),
            HumanMessage(content=query),
        ]
        executed_tool = False

        for turn in range(max_turns):
            response = (required_model if turn == 0 else automatic_model).invoke(messages)
            messages.append(response)
            if not response.tool_calls:
                if not executed_tool:
                    return '{"evidence": []}'
                return StrOutputParser().invoke(response)

            for call in response.tool_calls:
                selected = allowed.get(call["name"])
                status = "success"
                if selected is None:
                    content = f"Error: tool {call['name']} is not allowed for this query."
                    status = "error"
                else:
                    try:
                        content = selected.invoke(call["args"])
                        executed_tool = True
                    except Exception as exc:
                        content = f"Error: {call['name']} failed ({type(exc).__name__}). Do not invent evidence."
                        status = "error"
                messages.append(ToolMessage(
                    content=str(content), tool_call_id=call["id"],
                    name=call["name"], status=status,
                ))

        # Preserve the empty-evidence fallback when the turn budget is exhausted.
        return '{"evidence": []}'


def create_researcher_agent(search_type: SearchType) -> ResearcherToolLoop:
    """Expose only the tools permitted by the existing SearchType router."""
    routed = ToolRouter().route(search_type)
    available = {"paper_search": paper_search, "web_search": web_search}
    return ResearcherToolLoop(tools=[available[name] for name in routed.tools])
