"""Render citation metadata from stored evidence, without model calls."""

import logging
import re

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


def append_references(report: str, evidence: list[Evidence]) -> str:
    """Replace generated reference sections with trusted cited metadata.

    Unknown IDs remain in the body for future citation validation, but never
    acquire fabricated references. No citations means no reference section.
    """
    body = report_body(report)
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
