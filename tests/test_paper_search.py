from models.academic_paper import (
    AcademicPaper,
)

import tools.paper_search as paper_search_module

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