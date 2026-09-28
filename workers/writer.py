from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from llm import get_model


WRITER_INSTRUCTIONS = """
你是 DeepResearch 系统中的 Writer Agent。

你的职责是根据已经收集到的研究证据生成结构化研究报告。

你不能调用搜索工具，也不能补充未经证据支持的信息。

写作要求：

1. 必须回答用户原始研究问题。
2. 只能使用输入中提供的 Evidence。
3. 不要编造论文、作者、年份、引用量、DOI 或研究结论。
4. 如果证据不足，要明确说明。
5. 对引用量等动态数据，要说明其来源和时间敏感性。
6. 优先使用 verified=true 的 Evidence。
7. verified=false 的 Evidence 只能作为补充参考，并明确降低可信度。
8. 避免重复讨论同一篇论文。
9. 保持结构清晰、信息密度高。
10. 不要提及你是 AI。
11. 不要执行任何搜索。

报告建议结构：

# Research Report

## 研究问题

## 核心结论

## 论文清单

## 主要研究方向与趋势

## 证据与可信度说明

## 局限性

如果用户的问题非常具体，可以适当调整结构，但必须保持清晰。
"""


writer_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=WRITER_INSTRUCTIONS),
    ("human", "{prompt}"),
])


def create_writer_chain() -> Runnable[dict[str, str], str]:
    """Create Prompt -> Chat Model -> string output without search tools."""
    return writer_prompt | get_model() | StrOutputParser()
