from memory.memory_item import (
    MemoryItem,
)

from memory.memory_store import (
    MemoryStore,
)



def test_memory_item_default_values():

    item = MemoryItem(
        question="test"
    )


    assert (
        item.question
        ==
        "test"
    )


    assert (
        item.evidence_count
        ==
        0
    )



def test_memory_store_add():

    store = MemoryStore()


    item = MemoryItem(
        question=
        "GNN multimodal recommendation"
    )


    store.add(
        item
    )


    assert len(store) == 1



def test_memory_store_keyword_search():

    store = MemoryStore()


    store.add(
        MemoryItem(
            question=
            "Graph Neural Network Recommendation"
        )
    )


    store.add(
        MemoryItem(
            question=
            "Large Language Model"
        )
    )


    results = store.search(
        "Graph"
    )


    assert len(results)==1



def test_memory_can_save_and_load(tmp_path):

    from memory.memory_storage import (
        save_memory,
        load_memory,
    )


    path = (
        tmp_path
        /
        "memory.json"
    )


    item = MemoryItem(
        question="test memory",
        summary="hello",
        evidence_count=3,
    )


    save_memory(
        [item],
        path,
    )


    loaded = load_memory(
        path,
    )


    assert len(loaded)==1


    assert (
        loaded[0].question
        ==
        "test memory"
    )