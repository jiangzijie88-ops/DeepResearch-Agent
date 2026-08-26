import os
import time
import threading

import requests
from dotenv import load_dotenv
from agents import function_tool


load_dotenv()


OPENALEX_API_URL = "https://api.openalex.org/works"

MAX_PAPER_SEARCHES = 3

_paper_search_count = 0
_paper_search_lock = threading.Lock()
_seen_paper_ids = set()
_seen_paper_lock = threading.Lock()

_request_lock = threading.Lock()

MIN_REQUEST_INTERVAL = 1.0

_last_request_time = 0.0


def reset_paper_search_count():
    global _paper_search_count

    with _paper_search_lock:
        _paper_search_count = 0

    with _seen_paper_lock:
        _seen_paper_ids.clear()


def _wait_for_rate_limit():
    """
    Ensure OpenAlex requests are not sent too quickly.
    """
    global _last_request_time

    with _request_lock:
        now = time.time()

        elapsed = now - _last_request_time

        if elapsed < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - elapsed

            print(
                f"[Rate Limit] Waiting "
                f"{wait_time:.2f} seconds..."
            )

            time.sleep(wait_time)

        _last_request_time = time.time()


def _reconstruct_abstract(
    inverted_index: dict | None,
) -> str:
    """
    Reconstruct plain-text abstract from
    OpenAlex abstract_inverted_index.
    """

    if not inverted_index:
        return ""

    word_positions = []

    for word, positions in inverted_index.items():

        for position in positions:
            word_positions.append(
                (position, word)
            )

    word_positions.sort(
        key=lambda item: item[0]
    )

    abstract = " ".join(
        word
        for _, word in word_positions
    )

    return abstract




def _calculate_relevance_score(
    work: dict,
) -> tuple[bool, int]:
    """
    First apply hard relevance gates,
    then calculate a soft relevance score.

    Returns:
        (passed_hard_gate, relevance_score)
    """

    title = (
        work.get("title")
        or ""
    ).lower()

    abstract = _reconstruct_abstract(
        work.get("abstract_inverted_index")
    ).lower()

    topics = work.get("topics") or []

    topic_text = " ".join(
        topic.get("display_name", "")
        for topic in topics
    ).lower()

    full_text = (
        title
        + " "
        + abstract
        + " "
        + topic_text
    )

    # =========================================
    # 1. Recommendation evidence
    # =========================================
    recommendation_keywords = [
        "recommendation",
        "recommender",
        "recommend",
        "collaborative filtering",
    ]

    has_recommendation = any(
        keyword in full_text
        for keyword in recommendation_keywords
    )

    # =========================================
    # 2. Multimodal evidence
    # =========================================
    multimodal_keywords = [
        "multimodal",
        "multi-modal",
        "multimedia",
        "multiple modalities",
        "visual and textual",
        "visual modality",
        "textual modality",
    ]

    has_multimodal = any(
        keyword in full_text
        for keyword in multimodal_keywords
    )

    # =========================================
    # 3. Graph / GNN evidence
    # =========================================
    graph_keywords = [
        "graph neural network",
        "graph convolution",
        "graph attention",
        "graph learning",
        "graph-based",
        "gnn",
    ]

    has_graph = any(
        keyword in full_text
        for keyword in graph_keywords
    )

    # =========================================
    # Hard Gate
    # =========================================
    passed_hard_gate = (
        has_recommendation
        and has_multimodal
        and has_graph
    )

    if not passed_hard_gate:
        return False, 0

    # =========================================
    # Soft Score
    # =========================================
    score = 0

    # Recommendation
    if any(
        keyword in title
        for keyword in recommendation_keywords
    ):
        score += 3
    else:
        score += 1

    # Multimodal
    if any(
        keyword in title
        for keyword in multimodal_keywords
    ):
        score += 3
    else:
        score += 1

    # Graph / GNN
    if any(
        keyword in title
        for keyword in graph_keywords
    ):
        score += 3
    else:
        score += 1

    return True, score

@function_tool
def paper_search(
    query: str,
    start_year: int,
    end_year: int,
) -> str:
    """
    Search academic papers using OpenAlex.

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

    api_key = os.getenv("OPENALEX_API_KEY")

    if not api_key:
        print("[Tool Error] OPENALEX_API_KEY not found.")

        return (
            "OpenAlex API key is missing. "
            "Academic metadata cannot be verified."
        )

    # =========================================
    # Hard year filtering in OpenAlex  是否有资格进入候选集
    # =========================================
    openalex_filter = (
        f"from_publication_date:{start_year}-01-01,"
        f"to_publication_date:{end_year}-12-31"
    )

    params = {
        "search": query,
        "filter": openalex_filter,
        "per_page": 10,
        "sort": "relevance_score:desc",
        "api_key": api_key,
    }

    # =========================================
    # Retry with backoff
    # =========================================
    max_retries = 3

    response = None

    for attempt in range(max_retries):

        _wait_for_rate_limit()

        try:

            response = requests.get(
                OPENALEX_API_URL,
                params=params,
                timeout=15,
            )

            if response.status_code == 429:

                wait_seconds = 2 ** attempt

                print(
                    f"[OpenAlex 429] Rate limited. "
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

                continue

            response.raise_for_status()

            break

        except requests.RequestException as e:

            print(
                f"[OpenAlex Error] "
                f"Attempt {attempt + 1}/{max_retries}: {e}"
            )

            if attempt == max_retries - 1:
                return (
                    "Academic paper search failed. "
                    "Do not invent metadata."
                )

            wait_seconds = 2 ** attempt

            print(
                f"[Retry] Waiting "
                f"{wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)

    if response is None or response.status_code == 429:

        print(
            "[Tool Error] OpenAlex is still rate limited "
            "after retries."
        )

        return (
            "OpenAlex remained rate-limited. "
            "Citation data could not be verified."
        )

    # =========================================
    # Parse result
    # =========================================
    try:
        data = response.json()

    except ValueError:

        print("[Tool Error] Invalid JSON from OpenAlex.")

        return (
            "OpenAlex returned invalid data."
        )

    works = data.get("results", [])

    if not works:
        print("[Tool Result] No papers found.")
        return "No academic papers found."

    # =========================================
    # Topic relevance filtering
    # =========================================
    relevant_works = []

    for work in works:

        title = work.get("title") or ""

        year = work.get("publication_year")

        if not year:
            continue

        if year < start_year or year > end_year:
            continue

        passed_hard_gate, relevance_score = (
            _calculate_relevance_score(work)
        )

        if not passed_hard_gate:
            print(
                f"[Hard Filter] "
                f"Skipping irrelevant paper: "
                f"{title}"
            )
            continue

        work["_relevance_score"] = relevance_score

        # =========================================
        # Deduplicate papers across search calls
        # =========================================
        doi = work.get("doi")

        if doi:
            paper_id = doi.lower()
        else:
            paper_id = (
                work.get("id")
                or title
                or ""
            ).lower()

        with _seen_paper_lock:

            if paper_id in _seen_paper_ids:
                print(
                    f"[Dedup] Skipping already seen paper: "
                    f"{title}"
                )
                continue

            _seen_paper_ids.add(paper_id)

        relevant_works.append(work)

    relevant_works.sort(
        key=lambda work: work.get(
            "_relevance_score",
            0,
        ),
        reverse=True,
    )

    if not relevant_works:

        print(
            "[Tool Result] Papers were returned by OpenAlex, "
            "but none passed relevance filtering."
        )

        return (
            "OpenAlex returned papers, "
            "but none matched the requested topic "
            "after year and relevance filtering."
        )

    # 最终最多返回 5 篇
    relevant_works = relevant_works[:5]

    formatted_results = []

    for i, work in enumerate(
        relevant_works,
        start=1,
    ):

        title = work.get("title") or "Unknown title"

        year = (
            work.get("publication_year")
            or "Unknown year"
        )

        citations = work.get("cited_by_count")

        if citations is None:
            citation_text = "Unknown"
        else:
            citation_text = str(citations)

        relevance_score = work.get(
            "_relevance_score",
            0,
        )

        doi = work.get("doi") or "No DOI"

        authorships = work.get("authorships", [])

        authors = []

        for authorship in authorships[:5]:

            author = authorship.get("author") or {}

            name = author.get("display_name")

            if name:
                authors.append(name)

        if authors:
            author_text = ", ".join(authors)
        else:
            author_text = "Unknown authors"

        primary_location = (
            work.get("primary_location")
            or {}
        )

        url = (
            primary_location.get("landing_page_url")
            or doi
            or "No URL"
        )

        formatted_result = (
            f"Paper {i}\n"
            f"Title: {title}\n"
            f"Authors: {author_text}\n"
            f"Year: {year}\n"
            f"Citations: {citation_text}\n"
            f"Relevance Score: {relevance_score}\n"
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