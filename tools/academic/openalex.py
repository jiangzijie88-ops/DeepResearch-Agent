import os
import time

import requests

from models.academic_paper import (
    AcademicPaper,
)

OPENALEX_WORKS_URL = (
    "https://api.openalex.org/works"
)

def reconstruct_openalex_abstract(
    inverted_index: dict | None,
) -> str | None:

    if not inverted_index:
        return None

    word_positions = []

    for word, positions in (
        inverted_index.items()
    ):

        for position in positions:

            word_positions.append(
                (
                    position,
                    word,
                )
            )

    word_positions.sort(
        key=lambda item: item[0]
    )

    abstract = " ".join(
        word
        for _, word
        in word_positions
    )

    return (
        abstract
        or None
    )


def parse_openalex_work(
    work: dict,
) -> AcademicPaper:
    title = (
        work.get("title")
        or "Unknown title"
    )

    authors = []

    for authorship in (
        work.get("authorships")
        or []
    ):
        author = (
            authorship.get("author")
            or {}
        )

        name = author.get(
            "display_name"
        )

        if name:
            authors.append(
                name
            )

    primary_location = (
        work.get("primary_location")
        or {}
    )

    source_info = (
        primary_location.get("source")
        or {}
    )

    venue = source_info.get(
        "display_name"
    )

    url = (
        primary_location.get(
            "landing_page_url"
        )
        or work.get("doi")
    )

    return AcademicPaper(
        title=title,

        authors=authors,

        year=work.get(
            "publication_year"
        ),

        citations=work.get(
            "cited_by_count"
        ),

        doi=work.get(
            "doi"
        ),

        url=url,

        venue=venue,

        published_at=work.get(
            "publication_date"
        ),

        abstract=(
            reconstruct_openalex_abstract(
                work.get(
                    "abstract_inverted_index"
                )
            )
        ),

        source="OpenAlex",
    )


def search_openalex(
    query: str,
    year_start: int | None = None,
    year_end: int | None = None,
    per_page: int = 10,
    api_key: str | None = None,
    request_get=requests.get,
    sleep=time.sleep,
    max_attempts: int = 3,
) -> list[AcademicPaper]:

    params = {
        "search": query,
        "per_page": per_page,
    }

    if (
        year_start is not None
        and year_end is not None
    ):
        params["filter"] = (
            "from_publication_date:"
            f"{year_start}-01-01,"
            "to_publication_date:"
            f"{year_end}-12-31"
        )

    elif year_start is not None:

        params["filter"] = (
            "from_publication_date:"
            f"{year_start}-01-01"
        )

    elif year_end is not None:

        params["filter"] = (
            "to_publication_date:"
            f"{year_end}-12-31"
        )

    resolved_api_key = (
        api_key
        if api_key is not None
        else os.getenv(
            "OPENALEX_API_KEY"
        )
    )

    if resolved_api_key:
        params["api_key"] = (
            resolved_api_key
        )

    for attempt in range(
        max_attempts
    ):
        try:

            response = request_get(
                OPENALEX_WORKS_URL,
                params=params,
                timeout=15,
            )

        except requests.RequestException as e:

            raise RuntimeError(
                "OpenAlex network error."
            ) from e

        if response.status_code == 429:

            if (
                attempt
                < max_attempts - 1
            ):
                delay = 2 ** attempt

                sleep(
                    delay
                )

                continue

            raise RuntimeError(
                "OpenAlex rate limit exceeded "
                "after maximum retry attempts."
            )

        if (
            response.status_code
            >= 400
        ):
            raise RuntimeError(
                "OpenAlex request failed "
                f"with HTTP status "
                f"{response.status_code}."
            )

        payload = response.json()

        raw_results = (
            payload.get("results")
            or []
        )

        return [
            parse_openalex_work(
                work
            )
            for work in raw_results
        ]

    return []


