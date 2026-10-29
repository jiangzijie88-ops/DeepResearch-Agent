"""Render citation metadata from stored evidence, without model calls."""

import logging
import re
from urllib.parse import quote, urlsplit

from models.evidence import Evidence


logger = logging.getLogger(__name__)
CITATION_PATTERN = re.compile(r"\[(E[1-9][0-9]*)\]")
REFERENCE_SECTION = re.compile(
    r"^##[ \t]+(?:References|参考证据|参考文献)[ \t]*\r?$.*?(?=^#{1,2}[ \t]|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


def extract_citation_ids(text: str) -> list[str]:
    """Return unique citation IDs in first appearance order."""
    return list(dict.fromkeys(CITATION_PATTERN.findall(text)))


def report_body(report: str) -> str:
    """Separate the programmatic reference section from report prose."""
    return REFERENCE_SECTION.sub("", report).rstrip()


def link_paper_titles(body: str, evidence: list[Evidence]) -> str:
    """Link exact cited titles using stored addresses, preserving Markdown links/code."""
    cited = set(extract_citation_ids(body))
    links = {}
    for item in evidence:
        if item.evidence_id not in cited or not item.title:
            continue
        candidates = []
        if item.doi:
            doi = item.doi.strip()
            if doi.startswith("10."):
                candidates.append("https://doi.org/" + doi)
            elif doi.startswith(("https://doi.org/", "http://doi.org/")):
                candidates.append(doi)
        if item.url:
            candidates.append(item.url.strip())
        for url in candidates:
            parsed = urlsplit(url)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                links[item.title] = quote(url, safe=":/?#[]@!$&'*+,;=%~_-.")
                break
    if not links:
        return body
    titles = "|".join(re.escape(title) for title in sorted(links, key=len, reverse=True))
    # Match protected Markdown first so repeated processing cannot nest links.
    pattern = re.compile(
        r"(?P<protected>```[\s\S]*?```|~~~[\s\S]*?~~~|`+[^`\n]*`+|"
        r"!?\[(?:\\.|[^\]\\\n])*\]\((?:\\.|[^)\\\n])*\)|"
        r"\[[^\]\n]+\]\[[^\]\n]*\])|(?P<title>" + titles + r")"
    )

    def replace(match):
        title = match.group("title")
        if title is None:
            return match.group(0)
        label = re.sub(r"([\\\[\]])", r"\\\1", title)
        return f"[{label}]({links[title]})"

    return pattern.sub(replace, body)


def append_references(report: str, evidence: list[Evidence]) -> str:
    """Replace generated reference sections with trusted cited metadata.

    Unknown IDs remain in the body for future citation validation, but never
    acquire fabricated references. No citations means no reference section.
    """
    body = link_paper_titles(report_body(report), evidence)
    lookup = {item.evidence_id: item for item in evidence if item.evidence_id}
    entries = []
    for evidence_id in extract_citation_ids(body):
        item = lookup.get(evidence_id)
        if item is None:
            logger.warning("Citation %s has no stored evidence; reference omitted.", evidence_id)
            continue
        metadata = [item.title]
        if item.authors:
            metadata.append(", ".join(item.authors))
        if item.year is not None:
            metadata.append(str(item.year))
        if item.venue:
            metadata.append(item.venue)
        lines = [f"[{evidence_id}] " + ". ".join(metadata) + "."]
        for label, value in [("Source", item.source), ("DOI", item.doi), ("URL", item.url)]:
            if value:
                lines.append(f"{label}: {value}")
        entries.append("  \n".join(lines))
    if not entries:
        return body
    return body + "\n\n## References\n\n" + "\n\n".join(entries)
