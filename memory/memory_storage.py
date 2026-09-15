import json
import os

from memory.memory_item import (
    MemoryItem,
)



def save_memory(
    items: list[MemoryItem],
    path: str,
):

    data = [
        item.model_dump()
        for item in items
    ]


    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )



def load_memory(
    path: str,
) -> list[MemoryItem]:


    if not os.path.exists(path):

        return []


    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)


    return [
        MemoryItem.model_validate(
            item
        )

        for item in data
    ]