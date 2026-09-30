import time
import threading

from dotenv import load_dotenv
from langchain_core.tools import tool
from tools.academic.relevance import rank_papers

from tools.academic.aggregator import (
    search_academic_papers,
)


load_dotenv()


MAX_PAPER_SEARCHES = 3

_paper_search_count = 0
_paper_search_lock = threading.Lock()
_seen_paper_ids = set()
_seen_paper_lock = threading.Lock()


def reset_paper_search_count():
    global _paper_search_count

    with _paper_search_lock:
        _paper_search_count = 0

    with _seen_paper_lock:
        _seen_paper_ids.clear()



def _search_academic_sources(
    query: str,
    start_year: int,
    end_year: int,
):
    return search_academic_papers(
        query=query,
        year_start=start_year,
        year_end=end_year,
        limit_per_source=10,
    )

@tool
def paper_search(
    query: str,
    start_year: int,
    end_year: int,
) -> str:
    """
    Search academic papers using multiple academic sources.

    Args:
        query: Academic paper search query.
        start_year: Earliest publication year.
        end_year: Latest publication year.
    """

    global _paper_search_count

    # =========================================
    # Validate year range
    # =========================================
    if start_year > end_year:
        return (
            "Invalid year range: "
            "start_year must be <= end_year."
        )

    # =========================================
    # Hard paper-search limit
    # =========================================
    with _paper_search_lock:

        if _paper_search_count >= MAX_PAPER_SEARCHES:

            print("\n" + "=" * 60)
            print("[Tool Blocked] paper_search")
            print(
                f"[Reason] Paper search limit reached "
                f"({MAX_PAPER_SEARCHES}/{MAX_PAPER_SEARCHES})"
            )
            print("=" * 60 + "\n")

            return (
                "Academic paper search limit has been reached. "
                "Do not call paper_search again. "
                "Use the verified papers already collected."
            )

        _paper_search_count += 1
        current_search = _paper_search_count

    print("\n" + "=" * 60)
    print(
        f"[Tool Call] paper_search "
        f"({current_search}/{MAX_PAPER_SEARCHES})"
    )
    print(f"[Query] {query}")
    print(
        f"[Year Filter] "
        f"{start_year} - {end_year}"
    )
    print("=" * 60)

    # =========================================
    # Search academic providers
    # =========================================
    try:
        papers = _search_academic_sources(
            query=query,
            start_year=start_year,
            end_year=end_year,
        )

    except RuntimeError as e:

        print(
            f"[Academic Search Error] {e}"
        )

        return (
            "All academic paper search providers "
            "failed. Do not invent metadata."
        )


    if not papers:
        print(
            "[Tool Result] "
            "No academic papers found."
        )

        return (
            "No academic papers found."
        )

    # =========================================
    # Year filtering and deduplication
    # =========================================
    candidate_papers = []

    for paper in papers:

        title = paper.title or ""

        year = paper.year

        if year is None:
            continue

        if year < start_year or year > end_year:
            continue

        # =========================================
        # Deduplicate papers across search calls
        # =========================================
        doi = paper.doi

        if doi:
            paper_id = (
                doi
                .strip()
                .lower()
            )

        elif paper.url:
            paper_id = (
                paper.url
                .strip()
                .lower()
                .rstrip("/")
            )

        else:
            paper_id = (
                f"{paper.title}|{paper.year}"
                .strip()
                .lower()
            )

        with _seen_paper_lock:

            if paper_id in _seen_paper_ids:
                print(
                    f"[Dedup] Skipping already seen paper: "
                    f"{title}"
                )
                continue

            _seen_paper_ids.add(paper_id)

        candidate_papers.append(paper)

    if not candidate_papers:

        print(
            "[Tool Result] Academic papers were returned, "
            "but none remained after year filtering and deduplication."
        )

        return (
            "Academic search returned papers, "
            "but none remained after year filtering and deduplication."
        )

    # 最终最多返回 5 篇
    candidate_papers = [
        result.paper for result in rank_papers(query, candidate_papers)[:5]
    ]

    formatted_results = []

    for i, paper in enumerate(
        candidate_papers,
        start=1,
    ):

        title = (
            paper.title
            or "Unknown title"
        )

        year = (
            paper.year
            if paper.year is not None
            else "Unknown year"
        )

        published_at = (
            paper.published_at
            or "Unknown publication date"
        )

        citations = paper.citations

        if citations is None:
            citation_text = "Unknown"
        else:
            citation_text = str(
                citations
            )

        doi = (
            paper.doi
            or "No DOI"
        )

        if paper.authors:
            author_text = ", ".join(
                paper.authors[:5]
            )
        else:
            author_text = (
                "Unknown authors"
            )

        venue = (
            paper.venue
            or "Unknown venue"
        )

        url = (
            paper.url
            or paper.doi
            or "No URL"
        )

        formatted_result = (
            f"Paper {i}\n"
            f"Title: {title}\n"
            f"Authors: {author_text}\n"
            f"Year: {year}\n"
            f"Published At: {published_at}\n"
            f"Venue: {venue}\n"
            f"Citations: {citation_text}\n"
            f"Source: {paper.source}\n"
            f"DOI: {doi}\n"
            f"URL: {url}\n"
        )

        formatted_results.append(
            formatted_result
        )

    final_result = "\n".join(
        formatted_results
    )

    print("\n[Tool Result]")
    print(final_result)
    print("=" * 60 + "\n")

    return final_result
