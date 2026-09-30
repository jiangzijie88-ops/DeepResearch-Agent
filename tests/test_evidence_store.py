from models.evidence import Evidence
from models.evidence_store import EvidenceStore
import pytest

def make_evidence(
    *,
    title="Test Paper",
    year=2025,
    source="OpenAlex",
    doi=None,
    url=None,
    citations=10,
    authors=None,
    venue=None,
    published_at=None,
    summary="Test summary.",
    verified=True,
    query=None,
    retrieved_at=None,
    confidence=None,
):
    return Evidence(
        title=title,
        evidence_type="paper",
        year=year,
        citations=citations,
        source=source,
        doi=doi,
        url=url,
        summary=summary,
        verified=verified,
        authors=authors or [],
        venue=venue,
        published_at=published_at,
        query=query,
        retrieved_at=retrieved_at,
        confidence=confidence,
    )


def test_evidence_store_preserves_provenance_metadata():
    evidence = Evidence(
        title="Provenance Paper",
        evidence_type="paper",
        year=2025,
        citations=10,
        source="OpenAlex",
        doi="10.1000/provenance",
        url="https://example.com/provenance",
        summary="测试 provenance。",
        verified=True,
        query="original query",
        retrieved_at="2026-08-31T02:30:00+00:00",
    )

    store = EvidenceStore()

    store.add_many(
        [evidence]
    )

    stored = store.get_all()[0]

    assert stored.query == "original query"

    assert (
        stored.retrieved_at
        == "2026-08-31T02:30:00+00:00"
    )

def test_evidence_store_deduplicates_same_doi():
    first = make_evidence(
        title="Same Paper",
        doi="https://doi.org/10.1000/Test.DOI",
        source="OpenAlex",
    )

    second = make_evidence(
        title="Same Paper",
        doi="10.1000/test.doi",
        source="Semantic Scholar",
    )

    store = EvidenceStore()

    added_first = store.add_many(
        [first]
    )

    added_second = store.add_many(
        [second]
    )

    assert added_first == 1
    assert added_second == 0
    assert store.count() == 1


def test_evidence_store_deduplicates_same_url():
    first = make_evidence(
        title="Web Paper",
        doi=None,
        url="https://example.com/paper",
        source="Web Search",
    )

    second = make_evidence(
        title="Web Paper",
        doi=None,
        url="https://example.com/paper/",
        source="Another Source",
    )

    store = EvidenceStore()

    store.add_many(
        [first]
    )

    added = store.add_many(
        [second]
    )

    assert added == 0
    assert store.count() == 1

def test_evidence_store_deduplicates_normalized_title_and_year():
    first = make_evidence(
        title=(
            "LGMRec: Local and Global Graph "
            "Learning for Multimodal Recommendation"
        ),
        year=2024,
        doi=None,
        url=None,
    )

    second = make_evidence(
        title=(
            "LGMRec - Local and Global Graph "
            "Learning for Multimodal Recommendation"
        ),
        year=2024,
        doi=None,
        url=None,
    )

    store = EvidenceStore()

    store.add_many(
        [first]
    )

    added = store.add_many(
        [second]
    )

    assert added == 0
    assert store.count() == 1


def test_evidence_store_keeps_same_title_with_different_years():
    first = make_evidence(
        title="Annual Recommendation Survey",
        year=2024,
        doi=None,
        url=None,
    )

    second = make_evidence(
        title="Annual Recommendation Survey",
        year=2025,
        doi=None,
        url=None,
    )

    store = EvidenceStore()

    added = store.add_many(
        [
            first,
            second,
        ]
    )

    assert added == 2
    assert store.count() == 2


def test_evidence_store_merges_duplicate_metadata():
    first = make_evidence(
        title="Merged Paper",
        year=2025,
        doi="10.1000/merge",
        url=None,
        source="OpenAlex",
        citations=10,
        authors=[],
        venue=None,
        published_at=None,
        verified=True,
        query="first query",
        retrieved_at="2026-08-31T01:00:00+00:00",
    )

    second = make_evidence(
        title="Merged Paper",
        year=2025,
        doi="https://doi.org/10.1000/merge",
        url="https://example.com/merged-paper",
        source="Semantic Scholar",
        citations=25,
        authors=[
            "Alice Zhang",
            "Bob Li",
        ],
        venue="SIGIR",
        published_at="2025-07-15",
        verified=True,
        query="second query",
        retrieved_at="2026-08-31T02:00:00+00:00",
    )

    store = EvidenceStore()

    store.add_many(
        [first]
    )

    added = store.add_many(
        [second]
    )

    assert added == 0
    assert store.count() == 1

    merged = store.get_all()[0]

    assert merged.authors == [
        "Alice Zhang",
        "Bob Li",
    ]

    assert merged.venue == "SIGIR"

    assert (
        merged.published_at
        == "2025-07-15"
    )

    assert (
        merged.url
        == "https://example.com/merged-paper"
    )

    assert merged.citations == 25


def test_evidence_store_merges_authors_without_duplicates():
    first = make_evidence(
        title="Author Merge Paper",
        year=2025,
        doi="10.1000/authors",
        authors=[
            "Alice Zhang",
        ],
    )

    second = make_evidence(
        title="Author Merge Paper",
        year=2025,
        doi="10.1000/authors",
        authors=[
            "Alice Zhang",
            "Bob Li",
        ],
    )

    store = EvidenceStore()

    store.add_many(
        [
            first,
            second,
        ]
    )

    merged = store.get_all()[0]

    assert merged.authors == [
        "Alice Zhang",
        "Bob Li",
    ]


def test_evidence_store_keeps_larger_citation_count():
    first = make_evidence(
        title="Citation Paper",
        doi="10.1000/citations",
        citations=12,
    )

    second = make_evidence(
        title="Citation Paper",
        doi="10.1000/citations",
        citations=27,
    )

    store = EvidenceStore()

    store.add_many(
        [
            first,
            second,
        ]
    )

    merged = store.get_all()[0]

    assert merged.citations == 27


def test_evidence_store_normalizes_doi_prefixes():
    first = make_evidence(
        doi=(
            "https://doi.org/"
            "10.1145/1234567"
        ),
    )

    second = make_evidence(
        doi="DOI:10.1145/1234567",
    )

    store = EvidenceStore()

    store.add_many(
        [
            first,
            second,
        ]
    )

    assert store.count() == 1


def test_ids_survive_duplicates_and_append():
    store = EvidenceStore()
    store.add_many([make_evidence(title="A", doi="10.1/a"), make_evidence(title="B")])
    store.add_many([make_evidence(title="A", doi="10.1/a", source="Semantic Scholar", venue="Venue")])
    store.add_many([make_evidence(title="C")])
    assert [e.evidence_id for e in store.get_all()] == ["E1", "E2", "E3"]
    assert store.get_all()[0].source == "OpenAlex | Semantic Scholar"
    assert store.get_all()[0].venue == "Venue"


def test_checkpoint_ids_restore_and_continue(tmp_path):
    from models.research_state import ResearchState
    from models.state_store import save_state, load_state
    store = EvidenceStore()
    store.add_many([make_evidence(title=str(i)) for i in range(10)])
    path = tmp_path / "state.json"
    save_state(ResearchState(question="test", evidence=store.get_all()), path)
    restored = EvidenceStore()
    restored.add_many(load_state(path).evidence)
    restored.add_many([make_evidence(title="new A"), make_evidence(title="new B")])
    assert [e.evidence_id for e in restored.get_all()] == [f"E{i}" for i in range(1, 13)]


def test_legacy_and_out_of_order_ids_do_not_collide():
    legacy = make_evidence(title="legacy")
    assigned = make_evidence(title="assigned")
    assigned = Evidence.model_validate(dict(assigned.model_dump(), evidence_id="E1"))
    store = EvidenceStore()
    store.add_many([legacy, assigned])
    assert [e.evidence_id for e in store.get_all()] == ["E2", "E1"]
    store.add_many([make_evidence(title="new")])
    assert store.get_all()[-1].evidence_id == "E3"


def test_conflicting_restored_ids_are_rejected():
    store = EvidenceStore()
    first = Evidence.model_validate(dict(make_evidence(title="A").model_dump(), evidence_id="E7"))
    second = Evidence.model_validate(dict(make_evidence(title="B").model_dump(), evidence_id="E7"))
    store.add_many([first])
    with pytest.raises(ValueError, match="E7"):
        store.add_many([second])
