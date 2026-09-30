import pytest

from models.academic_paper import (
    AcademicPaper,
)

import tools.paper_search as paper_search_module


@pytest.fixture(autouse=True)
def isolate_search_state(monkeypatch):
    monkeypatch.setattr(paper_search_module, "_paper_search_count", 0)
    monkeypatch.setattr(paper_search_module, "_seen_paper_ids", set())


@pytest.mark.parametrize("query,title", [
    (
        "graph neural network multimodal recommendation",
        "Multimodal Recommendation with Graph Neural Networks",
    ),
    (
        "retrieval augmented generation",
        "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
    ),
    (
        "medical image segmentation transformer",
        "Swin Transformer for Medical Image Segmentation",
    ),
    ("large language model agents", "Large Language Model Agents"),
    ("database query optimization", "Database Query Optimization"),
    ("diffusion model image generation", "Diffusion Models for Image Generation"),
])
@pytest.mark.parametrize("abstract", [None, "A study of methods and evaluation."])
def test_paper_search_accepts_topics_through_aggregator(monkeypatch, query, title, abstract):
    from tools.academic.aggregator import search_academic_papers

    def fake_openalex(query, year_start, year_end, per_page):
        assert (year_start, year_end, per_page) == (2020, 2026, 10)
        return [AcademicPaper(title=title, year=2025, abstract=abstract,
                              doi="10.1000/topic", source="OpenAlex")]

    def fake_semantic(query, year_start, year_end, limit):
        assert (year_start, year_end, limit) == (2020, 2026, 10)
        return [AcademicPaper(title=title, year=2025, authors=["Alice"],
                              doi="https://doi.org/10.1000/topic",
                              venue="Test Venue", source="Semantic Scholar")]

    def search_with_fake_providers(**kwargs):
        assert kwargs["query"] == query
        return search_academic_papers(
            **kwargs, openalex_search=fake_openalex,
            semantic_scholar_search=fake_semantic,
        )

    monkeypatch.setattr(paper_search_module, "search_academic_papers", search_with_fake_providers)
    result = paper_search_module.paper_search.invoke({
        "query": query, "start_year": 2020, "end_year": 2026,
    })

    assert result.count(f"Title: {title}\n") == 1
    assert "Authors: Alice" in result
    assert "Venue: Test Venue" in result
    assert "Source: OpenAlex | Semantic Scholar" in result


def test_paper_search_preserves_year_filter_order_and_limit(monkeypatch):
    papers = [
        AcademicPaper(title=f"Study {year}", year=year, source="OpenAlex")
        for year in [None, 2019, 2027, 2020, 2026, 2021, 2022, 2023, 2024]
    ]
    monkeypatch.setattr(paper_search_module, "search_academic_papers", lambda **kwargs: papers)
    result = paper_search_module.paper_search.invoke({
        "query": "any academic topic", "start_year": 2020, "end_year": 2026,
    })
    assert [line for line in result.splitlines() if line.startswith("Title:")] == [
        "Title: Study 2020", "Title: Study 2026", "Title: Study 2021",
        "Title: Study 2022", "Title: Study 2023",
    ]


@pytest.mark.parametrize("metadata", [
    {"doi": "10.1000/topic"}, {"url": "https://example.invalid/paper"}, {},
])
def test_paper_search_deduplicates_generic_papers_across_calls(monkeypatch, metadata):
    paper = AcademicPaper(title="Database Query Optimization", year=2025,
                          source="OpenAlex", **metadata)
    monkeypatch.setattr(paper_search_module, "search_academic_papers",
                        lambda **kwargs: [paper, paper.model_copy()])
    args = {"query": "database query optimization", "start_year": 2020, "end_year": 2026}
    assert paper_search_module.paper_search.invoke(args).count("Title:") == 1
    assert "Title:" not in paper_search_module.paper_search.invoke(args)

def test_ranking_uses_merged_metadata_before_top_k(monkeypatch):
    from tools.academic.aggregator import search_academic_papers

    def fake_openalex(**kwargs):
        return [
            AcademicPaper(title=f"Unrelated Study {i}", year=2025,
                          citations=10000, source="OpenAlex")
            for i in range(5)
        ] + [AcademicPaper(title="Knowledge-Intensive NLP Tasks", year=2025,
                           doi="10.1000/rag", source="OpenAlex")]

    def fake_semantic(**kwargs):
        return [
            AcademicPaper(title="Knowledge-Intensive NLP Tasks", year=2025,
                          abstract="Retrieval augmented generation", doi="10.1000/rag",
                          source="Semantic Scholar"),
            AcademicPaper(title="Retrieval-Augmented Generation", year=2025,
                          citations=10, source="Semantic Scholar"),
        ]

    def search(**kwargs):
        return search_academic_papers(**kwargs, openalex_search=fake_openalex,
                                      semantic_scholar_search=fake_semantic)

    monkeypatch.setattr(paper_search_module, "search_academic_papers", search)
    result = paper_search_module.paper_search.invoke({
        "query": "retrieval augmented generation", "start_year": 2020, "end_year": 2026,
    })
    assert [line for line in result.splitlines() if line.startswith("Title:")] == [
        "Title: Retrieval-Augmented Generation", "Title: Knowledge-Intensive NLP Tasks",
        "Title: Unrelated Study 0", "Title: Unrelated Study 1", "Title: Unrelated Study 2",
    ]
    assert "Source: OpenAlex | Semantic Scholar" in result


def fake_search_academic_papers(
    query,
    year_start,
    year_end,
    limit_per_source,
):
    assert query == "test query"

    assert year_start == 2024

    assert year_end == 2026

    assert limit_per_source == 10

    return [
        AcademicPaper(
            title="Aggregated Paper",
            year=2025,
            source=(
                "OpenAlex | "
                "Semantic Scholar"
            ),
        )
    ]


def test_search_academic_sources_uses_aggregator(
    monkeypatch,
):
    monkeypatch.setattr(
        paper_search_module,
        "search_academic_papers",
        fake_search_academic_papers,
    )

    papers = (
        paper_search_module
        ._search_academic_sources(
            query="test query",
            start_year=2024,
            end_year=2026,
        )
    )

    assert len(papers) == 1

    assert (
        papers[0].title
        == "Aggregated Paper"
    )

    assert (
        papers[0].source
        == (
            "OpenAlex | "
            "Semantic Scholar"
        )
    )
