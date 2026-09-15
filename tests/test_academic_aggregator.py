import pytest

from models.academic_paper import AcademicPaper

from tools.academic.aggregator import (
    merge_academic_papers,
    search_academic_papers,
)

def test_merge_academic_papers_deduplicates_same_doi():
    openalex_paper = AcademicPaper(
        title="Same Paper",
        authors=[
            "Alice Zhang",
        ],
        year=2025,
        citations=10,
        doi=(
            "https://doi.org/"
            "10.1000/test-paper"
        ),
        url=(
            "https://openalex.org/test"
        ),
        venue=None,
        published_at=None,
        abstract=None,
        source="OpenAlex",
    )

    semantic_paper = AcademicPaper(
        title="Same Paper",
        authors=[
            "Alice Zhang",
            "Bob Li",
        ],
        year=2025,
        citations=25,
        doi="10.1000/test-paper",
        url=(
            "https://www."
            "semanticscholar.org/"
            "paper/test"
        ),
        venue="SIGIR",
        published_at="2025-07-15",
        abstract=(
            "Semantic Scholar abstract."
        ),
        source="Semantic Scholar",
    )

    merged = merge_academic_papers(
        [
            openalex_paper,
            semantic_paper,
        ]
    )

    assert len(merged) == 1

    paper = merged[0]

    assert paper.authors == [
        "Alice Zhang",
        "Bob Li",
    ]

    assert paper.citations == 25

    assert paper.venue == "SIGIR"

    assert (
        paper.published_at
        == "2025-07-15"
    )

    assert (
        paper.abstract
        == "Semantic Scholar abstract."
    )

    assert (
        paper.source
        == "OpenAlex | Semantic Scholar"
    )


def test_merge_academic_papers_deduplicates_title_and_year_without_doi():
    first = AcademicPaper(
        title=(
            "LGMRec: Local and Global Graph "
            "Learning for Multimodal Recommendation"
        ),
        year=2024,
        source="OpenAlex",
    )

    second = AcademicPaper(
        title=(
            "LGMRec - Local and Global Graph "
            "Learning for Multimodal Recommendation"
        ),
        year=2024,
        source="Semantic Scholar",
    )

    merged = merge_academic_papers(
        [
            first,
            second,
        ]
    )

    assert len(merged) == 1

    assert (
        merged[0].source
        == "OpenAlex | Semantic Scholar"
    )


def test_merge_academic_papers_keeps_same_title_with_different_years():
    first = AcademicPaper(
        title="Annual Recommendation Survey",
        year=2024,
        source="OpenAlex",
    )

    second = AcademicPaper(
        title="Annual Recommendation Survey",
        year=2025,
        source="Semantic Scholar",
    )

    merged = merge_academic_papers(
        [
            first,
            second,
        ]
    )

    assert len(merged) == 2


def test_merge_academic_papers_keeps_different_dois_separate():
    first = AcademicPaper(
        title="Same Looking Paper",
        year=2025,
        doi="10.1000/version-a",
        source="OpenAlex",
    )

    second = AcademicPaper(
        title="Same Looking Paper",
        year=2025,
        doi="10.1000/version-b",
        source="Semantic Scholar",
    )

    merged = merge_academic_papers(
        [
            first,
            second,
        ]
    )

    assert len(merged) == 2


def fake_openalex_search(
    query,
    year_start,
    year_end,
    per_page,
):
    return [
        AcademicPaper(
            title="Shared Paper",
            authors=[
                "Alice Zhang",
            ],
            year=2025,
            citations=10,
            doi="10.1000/shared",
            source="OpenAlex",
        ),

        AcademicPaper(
            title="OpenAlex Only Paper",
            year=2025,
            citations=5,
            doi="10.1000/openalex-only",
            source="OpenAlex",
        ),
    ]


def fake_semantic_scholar_search(
    query,
    year_start,
    year_end,
    limit,
):
    return [
        AcademicPaper(
            title="Shared Paper",
            authors=[
                "Alice Zhang",
                "Bob Li",
            ],
            year=2025,
            citations=20,
            doi=(
                "https://doi.org/"
                "10.1000/shared"
            ),
            venue="SIGIR",
            source="Semantic Scholar",
        ),

        AcademicPaper(
            title=(
                "Semantic Scholar "
                "Only Paper"
            ),
            year=2025,
            citations=8,
            doi=(
                "10.1000/"
                "semantic-only"
            ),
            source="Semantic Scholar",
        ),
    ]


def test_search_academic_papers_combines_both_sources():
    papers = search_academic_papers(
        query="multimodal recommendation",
        year_start=2024,
        year_end=2026,
        limit_per_source=10,
        openalex_search=(
            fake_openalex_search
        ),
        semantic_scholar_search=(
            fake_semantic_scholar_search
        ),
    )

    assert len(papers) == 3

    shared = next(
        paper
        for paper in papers
        if paper.title == "Shared Paper"
    )

    assert shared.citations == 20

    assert shared.authors == [
        "Alice Zhang",
        "Bob Li",
    ]

    assert shared.venue == "SIGIR"

    assert (
        shared.source
        == "OpenAlex | Semantic Scholar"
    )


def failing_openalex_search(
    query,
    year_start,
    year_end,
    per_page,
):
    raise RuntimeError(
        "OpenAlex unavailable"
    )


def test_search_academic_papers_continues_when_openalex_fails():
    papers = search_academic_papers(
        query="test query",
        year_start=2024,
        year_end=2026,
        openalex_search=(
            failing_openalex_search
        ),
        semantic_scholar_search=(
            fake_semantic_scholar_search
        ),
    )

    assert len(papers) == 2

    assert all(
        (
            "Semantic Scholar"
            in paper.source
        )
        for paper in papers
    )


def failing_semantic_scholar_search(
    query,
    year_start,
    year_end,
    limit,
):
    raise RuntimeError(
        "Semantic Scholar unavailable"
    )


def test_search_academic_papers_continues_when_semantic_scholar_fails():
    papers = search_academic_papers(
        query="test query",
        year_start=2024,
        year_end=2026,
        openalex_search=(
            fake_openalex_search
        ),
        semantic_scholar_search=(
            failing_semantic_scholar_search
        ),
    )

    assert len(papers) == 2

    assert all(
        "OpenAlex" in paper.source
        for paper in papers
    )




def empty_openalex_search(
    query,
    year_start,
    year_end,
    per_page,
):
    return []


def empty_semantic_scholar_search(
    query,
    year_start,
    year_end,
    limit,
):
    return []


def test_search_academic_papers_returns_empty_when_sources_succeed_without_results():
    papers = search_academic_papers(
        query="nothing found",
        year_start=2024,
        year_end=2026,
        openalex_search=(
            empty_openalex_search
        ),
        semantic_scholar_search=(
            empty_semantic_scholar_search
        ),
    )

    assert papers == []


class FakeReporter:

    def __init__(
        self,
    ):
        self.messages = []

    def __call__(
        self,
        message,
    ):
        self.messages.append(
            message
        )


def test_search_academic_papers_reports_semantic_scholar_failure():
    reporter = FakeReporter()

    papers = search_academic_papers(
        query="test query",
        year_start=2024,
        year_end=2026,
        openalex_search=(
            fake_openalex_search
        ),
        semantic_scholar_search=(
            failing_semantic_scholar_search
        ),
        reporter=reporter,
    )

    assert len(papers) == 2

    assert any(
        (
            "Semantic Scholar"
            in message
        )
        for message
        in reporter.messages
    )