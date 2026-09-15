import os
import time

import requests

from models.academic_paper import (
    AcademicPaper,
)

SEMANTIC_SCHOLAR_SEARCH_URL = (
    "https://api.semanticscholar.org/"
    "graph/v1/paper/search"
)


SEMANTIC_SCHOLAR_FIELDS = (
    "title,"
    "authors,"
    "year,"
    "citationCount,"
    "externalIds,"
    "url,"
    "venue,"
    "publicationDate,"
    "abstract"
)


def parse_semantic_scholar_paper(
    raw_paper: dict,
) -> AcademicPaper:

    authors = []

    for author in (
        raw_paper.get("authors")
        or []
    ):

        name = author.get(
            "name"
        )

        if name:
            authors.append(
                name
            )

    external_ids = (
        raw_paper.get("externalIds")
        or {}
    )

    doi = external_ids.get(
        "DOI"
    )

    return AcademicPaper(
        title=(
            raw_paper.get("title")
            or "Unknown title"
        ),

        authors=authors,

        year=raw_paper.get(
            "year"
        ),

        citations=raw_paper.get(
            "citationCount"
        ),

        doi=doi,

        url=raw_paper.get(
            "url"
        ),

        venue=raw_paper.get(
            "venue"
        ),

        published_at=raw_paper.get(
            "publicationDate"
        ),

        abstract=raw_paper.get(
            "abstract"
        ),

        source="Semantic Scholar",
    )

def search_semantic_scholar(
    query: str,
    year_start: int | None = None,
    year_end: int | None = None,
    limit: int = 10,
    api_key: str | None = None,
    request_get=requests.get,
    sleep=time.sleep,
    max_attempts: int = 3,
) -> list[AcademicPaper]:

    params = {
        "query": query,
        "limit": limit,
        "fields": (
            SEMANTIC_SCHOLAR_FIELDS
        ),
    }

    if (
        year_start is not None
        and year_end is not None
    ):
        params["year"] = (
            f"{year_start}-{year_end}"
        )

    elif year_start is not None:
        params["year"] = (
            f"{year_start}-"
        )

    elif year_end is not None:
        params["year"] = (
            f"-{year_end}"
        )

    resolved_api_key = (
        api_key
        if api_key is not None
        else os.getenv(
            "SEMANTIC_SCHOLAR_API_KEY"
        )
    )

    headers = {}

    if resolved_api_key:
        headers["x-api-key"] = (
            resolved_api_key
        )

    for attempt in range(
        max_attempts
    ):

        try:

            response = request_get(
                SEMANTIC_SCHOLAR_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=15,
            )

        except requests.RequestException as e:

            raise RuntimeError(
                "Semantic Scholar network error."
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
                "Semantic Scholar rate limit "
                "exceeded after maximum "
                "retry attempts."
            )

        if (
            response.status_code
            >= 400
        ):
            raise RuntimeError(
                "Semantic Scholar request "
                "failed with HTTP status "
                f"{response.status_code}."
            )

        payload = response.json()

        raw_results = (
            payload.get("data")
            or []
        )

        return [
            parse_semantic_scholar_paper(
                raw_paper
            )
            for raw_paper
            in raw_results
        ]

    return []