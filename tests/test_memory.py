from memory import (
    MemoryItem,
    save_memory,
    load_memory,
    build_memory_context,
)


def test_memory_item_default_values():

    item = MemoryItem(
        question="test"
    )

    assert item.question == "test"
    assert item.evidence_count == 0


def test_memory_can_save_and_load(
    tmp_path,
):

    path = (
        tmp_path
        / "memory.json"
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
        path
    )

    assert len(loaded) == 1

    assert (
        loaded[0].question
        == "test memory"
    )

    assert (
        loaded[0].summary
        == "hello"
    )

    assert (
        loaded[0].evidence_count
        == 3
    )


def test_build_memory_context():

    memories = [
        MemoryItem(
            question=(
                "Graph Neural Network "
                "Recommendation"
            ),
            summary=(
                "Research about GNN "
                "recommendation."
            ),
            evidence_count=5,
        ),
        MemoryItem(
            question=(
                "Large Language Model"
            ),
            summary="LLM research.",
            evidence_count=3,
        ),
    ]

    context = build_memory_context(
        memories,
        "Graph",
    )

    assert (
        "Graph Neural Network"
        in context
    )

    assert (
        "Evidence Count:"
        in context
    )


def test_build_memory_context_no_match():

    memories = [
        MemoryItem(
            question="Large Language Model"
        )
    ]

    context = build_memory_context(
        memories,
        "Graph",
    )

    assert (
        context
        ==
        "No previous research memory found."
    )