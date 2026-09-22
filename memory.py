import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """
    一条已完成研究任务的长期记忆。
    """

    question: str
    summary: str = ""
    evidence_count: int = 0

    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(
            timespec="seconds"
        )
    )


def save_memory(
    items: list[MemoryItem],
    path: str | Path,
) -> None:
    """
    将 memory 保存到 JSON 文件。
    """

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = [
        item.model_dump()
        for item in items
    ]

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_memory(
    path: str | Path,
) -> list[MemoryItem]:
    """
    从 JSON 文件加载 memory。
    """

    path = Path(path)

    if not path.exists():
        return []

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return [
        MemoryItem.model_validate(item)
        for item in data
    ]


def build_memory_context(
    memories: list[MemoryItem],
    keyword: str,
    limit: int = 3,
) -> str:
    """
    根据问题关键字寻找相关历史研究记录，
    并转换成 Planner 可使用的文本上下文。
    """

    keyword = keyword.strip().lower()

    matched = [
        memory
        for memory in memories
        if (
            keyword
            and keyword
            in memory.question.lower()
        )
    ][:limit]

    if not matched:
        return (
            "No previous research memory found."
        )

    blocks = []

    for index, memory in enumerate(
        matched,
        start=1,
    ):
        blocks.append(
            f"""Memory {index}

Question:
{memory.question}

Summary:
{memory.summary}

Evidence Count:
{memory.evidence_count}"""
        )

    return "\n\n".join(blocks)