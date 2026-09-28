import threading

from ddgs import DDGS
from langchain_core.tools import tool


MAX_SEARCHES = 3
_search_count = 0
_search_lock = threading.Lock()


SEARCH_BACKENDS = [
    "brave",
    "bing",
    "yahoo",
    "duckduckgo",
]


def reset_search_count():
    """
    Reset the search counter before starting a new research task.
    """
    global _search_count

    with _search_lock:
        _search_count = 0


@tool
def web_search(query: str) -> str:
    """
    Search the web for up-to-date information.

    Args:
        query: The search query.
    """

    global _search_count

    # -------------------------
    # Hard search limit
    # -------------------------
    with _search_lock:

        if _search_count >= MAX_SEARCHES:
            print("\n" + "=" * 60)
            print("[Tool Blocked] web_search")
            print(
                f"[Reason] Search limit reached "
                f"({MAX_SEARCHES}/{MAX_SEARCHES})"
            )
            print("=" * 60 + "\n")

            return (
                "Web search limit has been reached. "
                "Do not call web_search again. "
                "Use the information already collected "
                "and produce the final answer now."
            )

        _search_count += 1
        current_search = _search_count

    # -------------------------
    # Search logging
    # -------------------------
    print("\n" + "=" * 60)
    print(
        f"[Tool Call] web_search "
        f"({current_search}/{MAX_SEARCHES})"
    )
    print(f"[Query] {query}")
    print("=" * 60)

    # -------------------------
    # Backend fallback
    # -------------------------
    results = None

    for backend in SEARCH_BACKENDS:

        print(f"[Search Backend] Trying: {backend}")

        try:
            current_results = DDGS(timeout=10).text(
                query=query,
                max_results=5,
                backend=backend,
            )

            if current_results:
                results = current_results

                print(
                    f"[Search Backend] Success: {backend}"
                )

                break

            print(
                f"[Search Backend] No results: {backend}"
            )

        except Exception as e:
            print(
                f"[Search Backend] Failed: "
                f"{backend} -> {e}"
            )

    # -------------------------
    # All backends failed
    # -------------------------
    if not results:
        print("[Tool Error] All search backends failed.")

        return (
            "Web search failed on all available search backends. "
            "Continue using previously collected information "
            "and clearly state that live search was unavailable."
        )

    # -------------------------
    # Format results
    # -------------------------
    formatted_results = []

    for i, item in enumerate(results, start=1):

        title = item.get("title", "")
        url = item.get("href", "")
        body = item.get("body", "")

        formatted_result = (
            f"Result {i}\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"Summary: {body}\n"
        )

        formatted_results.append(formatted_result)

    final_result = "\n".join(formatted_results)

    print("\n[Tool Result]")
    print(final_result)
    print("=" * 60 + "\n")

    return final_result
