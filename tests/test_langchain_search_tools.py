"""Ensure LangChain wrappers preserve the existing search implementations."""

from unittest.mock import Mock

import pytest
from langchain_core.tools import BaseTool
from pydantic import ValidationError

from models.academic_paper import AcademicPaper
import tools.paper_search as papers
import tools.web_search as web


@pytest.fixture(autouse=True)
def isolate_budgets(monkeypatch):
    monkeypatch.setattr(web, "_search_count", 0)
    monkeypatch.setattr(papers, "_paper_search_count", 0)
    monkeypatch.setattr(papers, "_seen_paper_ids", set())


def test_web_tool_preserves_fallback_and_budget(monkeypatch):
    calls = []

    class FakeDDGS:
        def __init__(self, timeout):
            assert timeout == 10

        def text(self, query, max_results, backend):
            calls.append((query, backend))
            assert max_results == 5
            if backend == web.SEARCH_BACKENDS[0]:
                raise RuntimeError("backend unavailable")
            return [{"title": "Result", "href": "https://example.invalid", "body": "Snippet"}]

    monkeypatch.setattr(web, "DDGS", FakeDDGS)
    assert isinstance(web.web_search, BaseTool)
    for _ in range(web.MAX_SEARCHES):
        result = web.web_search.invoke({"query": "query"})
        assert "Title: Result" in result and "Summary: Snippet" in result
    assert "limit has been reached" in web.web_search.invoke({"query": "blocked"})
    assert calls == [("query", backend) for _ in range(web.MAX_SEARCHES)
                     for backend in web.SEARCH_BACKENDS[:2]]
    web.reset_search_count()
    assert "Title: Result" in web.web_search.invoke({"query": "new task"})


def test_web_tool_preserves_all_backends_failed_fallback(monkeypatch):
    client = Mock()
    client.text.side_effect = RuntimeError("offline provider failure")
    monkeypatch.setattr(web, "DDGS", lambda **kwargs: client)
    assert "failed on all" in web.web_search.invoke({"query": "query"})
    assert client.text.call_count == len(web.SEARCH_BACKENDS)


def test_paper_tool_preserves_metadata_dedup_budget_and_reset(monkeypatch):
    provider = Mock(return_value=[AcademicPaper(
        title="Multimodal Recommendation with Graph Neural Networks",
        year=2025, source="OpenAlex | Semantic Scholar", authors=["Alice"],
        venue="SIGIR", published_at="2025-07-01", citations=12,
        doi="10.1000/test", url="https://example.invalid/paper",
    )])
    monkeypatch.setattr(papers, "search_academic_papers", provider)
    args = {"query": "multimodal recommendation", "start_year": 2024, "end_year": 2026}
    assert isinstance(papers.paper_search, BaseTool)
    result = papers.paper_search.invoke(args)
    for expected in ["Authors: Alice", "Citations: 12", "Venue: SIGIR",
                     "Published At: 2025-07-01", "Source: OpenAlex | Semantic Scholar"]:
        assert expected in result
    provider.assert_called_once_with(
        query=args["query"], year_start=2024, year_end=2026, limit_per_source=10,
    )
    for _ in range(papers.MAX_PAPER_SEARCHES - 1):
        assert "Title:" not in papers.paper_search.invoke(args)
    assert "limit has been reached" in papers.paper_search.invoke(args)
    assert provider.call_count == papers.MAX_PAPER_SEARCHES
    papers.reset_paper_search_count()
    assert "Title:" in papers.paper_search.invoke(args)


def test_paper_tool_preserves_year_validation_and_provider_failure(monkeypatch):
    provider = Mock(side_effect=RuntimeError("all sources failed"))
    monkeypatch.setattr(papers, "search_academic_papers", provider)
    assert "Invalid year range" in papers.paper_search.invoke({
        "query": "query", "start_year": 2026, "end_year": 2024,
    })
    provider.assert_not_called()
    assert papers._paper_search_count == 0
    assert "failed" in papers.paper_search.invoke({
        "query": "query", "start_year": 2024, "end_year": 2026,
    })


def test_tool_schema_rejects_missing_arguments_before_search():
    with pytest.raises(ValidationError):
        papers.paper_search.invoke({"query": "missing years"})
    with pytest.raises(ValidationError):
        web.web_search.invoke({})
    assert papers._paper_search_count == 0
    assert web._search_count == 0
