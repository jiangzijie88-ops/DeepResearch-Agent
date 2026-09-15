import re

from models.academic_paper import (
    AcademicPaper,
)

from tools.academic.openalex import (
    search_openalex,
)

from tools.academic.semantic_scholar import (
    search_semantic_scholar,
)


def _normalize_doi(
    doi: str | None,
) -> str | None:
    if not doi:
        return None

    normalized = (
        doi
        .strip()
        .lower()
    )

    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    )

    for prefix in prefixes:
        if normalized.startswith(
            prefix
        ):
            normalized = normalized[
                len(prefix):
            ]

            break

    normalized = (
        normalized
        .strip()
        .rstrip("/")
    )

    return (
        normalized
        or None
    )


def _normalize_title(
    title: str | None,
) -> str:
    if not title:
        return ""

    normalized = (
        title
        .strip()
        .lower()
    )

    normalized = re.sub(
        r"[^\w\s]",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def _same_paper(
    first: AcademicPaper,
    second: AcademicPaper,
) -> bool:
    first_doi = _normalize_doi(
        first.doi
    )

    second_doi = _normalize_doi(
        second.doi
    )

    if first_doi and second_doi:
        return (
            first_doi
            == second_doi
        )

    first_title = _normalize_title(
        first.title
    )

    second_title = _normalize_title(
        second.title
    )

    if (
        not first_title
        or not second_title
    ):
        return False

    if first_title != second_title:
        return False

    if (
        first.year is not None
        and second.year is not None
    ):
        return (
            first.year
            == second.year
        )

    return True


def _merge_into(
    existing: AcademicPaper,
    incoming: AcademicPaper,
) -> None:
    merged_authors = list(
        existing.authors
    )

    for author in incoming.authors:
        if author not in merged_authors:
            merged_authors.append(
                author
            )

    existing.authors = (
        merged_authors
    )

    fields_to_fill = (
        "doi",
        "url",
        "venue",
        "published_at",
        "abstract",
    )

    for field_name in fields_to_fill:
        existing_value = getattr(
            existing,
            field_name,
        )

        incoming_value = getattr(
            incoming,
            field_name,
        )

        if (
            existing_value is None
            or existing_value == ""
        ):
            if (
                incoming_value is not None
                and incoming_value != ""
            ):
                setattr(
                    existing,
                    field_name,
                    incoming_value,
                )

    if (
        existing.year is None
        and incoming.year is not None
    ):
        existing.year = (
            incoming.year
        )

    if incoming.citations is not None:
        if (
            existing.citations is None
            or incoming.citations
            > existing.citations
        ):
            existing.citations = (
                incoming.citations
            )

    existing_sources = [
        source.strip()
        for source in (
            existing.source
            or ""
        ).split("|")
        if source.strip()
    ]

    incoming_sources = [
        source.strip()
        for source in (
            incoming.source
            or ""
        ).split("|")
        if source.strip()
    ]

    for source in incoming_sources:
        if source not in existing_sources:
            existing_sources.append(
                source
            )

    existing.source = " | ".join(
        existing_sources
    )


def merge_academic_papers(
    papers: list[AcademicPaper],
) -> list[AcademicPaper]:
    merged: list[AcademicPaper] = []

    for paper in papers:
        duplicate = None

        for existing in merged:
            if _same_paper(
                existing,
                paper,
            ):
                duplicate = existing

                break

        if duplicate is None:
            merged.append(
                paper.model_copy(
                    deep=True
                )
            )

        else:
            _merge_into(
                duplicate,
                paper,
            )

    return merged



def search_academic_papers(
    query: str,
    year_start: int | None = None,
    year_end: int | None = None,
    limit_per_source: int = 10,
    openalex_search=search_openalex,
    semantic_scholar_search=(
        search_semantic_scholar
    ),
    reporter=print,
) -> list[AcademicPaper]:

    papers: list[AcademicPaper] = []

    errors: list[str] = []

    # =========================================
    # OpenAlex
    # =========================================
    try:
        openalex_results = (
            openalex_search(
                query=query,
                year_start=year_start,
                year_end=year_end,
                per_page=limit_per_source,
            )
        )

        papers.extend(
            openalex_results
        )

    except RuntimeError as e:

        error_message = (
            f"[OpenAlex Provider Error] "
            f"{e}"
        )

        errors.append(
            error_message
        )

        reporter(
            error_message
        )

    # =========================================
    # Semantic Scholar
    # =========================================
    try:
        semantic_results = (
            semantic_scholar_search(
                query=query,
                year_start=year_start,
                year_end=year_end,
                limit=limit_per_source,
            )
        )

        papers.extend(
            semantic_results
        )

    except RuntimeError as e:

      error_message = (
          "[Semantic Scholar "
          "Provider Error] "
          f"{e}"
      )

      errors.append(
          error_message
      )

      reporter(
          error_message
      )

    # =========================================
    # Both providers failed
    # =========================================
    if (
        not papers
        and len(errors) == 2
    ):
        raise RuntimeError(
            "All academic search providers "
            "failed. "
            + " | ".join(errors)
        )

    return merge_academic_papers(
        papers
    )
