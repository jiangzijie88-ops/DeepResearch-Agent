from memory.memory_item import (
    MemoryItem,
)



def build_memory_context(
    memories: list[MemoryItem],
    keyword: str,
    limit: int = 3,
) -> str:


    matched = []


    for memory in memories:

        if (
            keyword.lower()
            in
            memory.question.lower()
        ):

            matched.append(
                memory
            )


    matched = matched[:limit]


    if not matched:

        return (
            "No previous research memory found."
        )


    lines = []


    for index, memory in enumerate(
        matched,
        start=1,
    ):

        lines.append(
            f"""
Memory {index}

Question:
{memory.question}

Summary:
{memory.summary}

Evidence Count:
{memory.evidence_count}
"""
        )


    return "\n".join(lines)