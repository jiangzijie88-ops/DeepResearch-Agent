"""Query-dependent lexical ranking without models, filtering, or I/O.

Exact token coverage favors titles (0.7) over abstracts (0.3). A contiguous
multi-token query phrase in the title adds 0.1, capped at 1. No stemming,
acronym expansion, or semantic similarity is inferred.
"""

import re
from dataclasses import dataclass

from models.academic_paper import AcademicPaper


# Keep technical acronyms and terms; only remove common query scaffolding.
STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "on", "in", "for", "to",
    "with", "by", "from", "recent", "research",
})
# Hyphens become token boundaries, including GPT-4 -> (gpt, 4).
# Preserve language names such as C++ and C# as distinct tokens from C.
TOKEN_PATTERN = re.compile(r"[^\W_]+(?:\+\+|#)?", re.UNICODE)


def normalize_query(text: str) -> str:
    """Lowercase, split punctuation, and collapse whitespace consistently."""
    return " ".join(TOKEN_PATTERN.findall(text.lower()))


def tokenize_query(query: str) -> tuple[str, ...]:
    """Return ordered unique content tokens, without dropping acronyms."""
    return tuple(dict.fromkeys(
        token for token in normalize_query(query).split()
        if token not in STOPWORDS
    ))


def score_paper(query: str, paper: AcademicPaper) -> float:
    """Return a [0, 1] lexical score; missing text and empty queries score 0."""
    query_tokens = tokenize_query(query)
    if not query_tokens:
        return 0.0

    title_tokens = normalize_query(paper.title or "").split()
    abstract_tokens = normalize_query(paper.abstract or "").split()
    terms = set(query_tokens)
    title_coverage = len(terms.intersection(title_tokens)) / len(terms)
    abstract_coverage = len(terms.intersection(abstract_tokens)) / len(terms)

    # Token sequence comparison avoids substring matches (RAG vs storage).
    phrase_length = len(query_tokens)
    phrase_match = phrase_length > 1 and any(
        tuple(title_tokens[i:i + phrase_length]) == query_tokens
        for i in range(len(title_tokens) - phrase_length + 1)
    )
    bonus = 0.1 if phrase_match else 0.0
    return min(1.0, 0.7 * title_coverage + 0.3 * abstract_coverage + bonus)


@dataclass(frozen=True)
class RankedPaper:
    """Keep query-specific scores separate from persistent paper metadata."""

    paper: AcademicPaper
    score: float


def rank_papers(query: str, papers: list[AcademicPaper]) -> list[RankedPaper]:
    """Rank all candidates; stable ties retain input order, including zeros.

    Citations and year never affect relevance. Neither the input list nor
    its paper metadata is changed. Callers apply their existing result limit.
    """
    scored = [RankedPaper(paper, score_paper(query, paper)) for paper in papers]
    return sorted(scored, key=lambda result: result.score, reverse=True)
