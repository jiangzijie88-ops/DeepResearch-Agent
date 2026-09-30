"""Deterministic citation checks and batched context for the existing Critic.

Existence is checked locally. Semantic support is supplied by the Critic,
never inferred from a citation's existence or from lexical overlap.
"""

import re

from models.critic_review import CitationClaim, CitationValidationResult, CriticIssue, CriticReview
from models.evidence import Evidence
from workflow.citations import CITATION_PATTERN, extract_citation_ids, report_body


def _text_units(report: str) -> list[str]:
    units, paragraph = [], []
    fence = None

    def flush():
        if paragraph:
            units.extend(re.split(r"(?<=[。！？!?])\s*|(?<=\.)\s+(?=[A-Z\u4e00-\u9fff])", " ".join(paragraph)))
            paragraph.clear()

    lines = report_body(report).splitlines()
    for index, raw in enumerate(lines):
        line = raw.strip()
        marker = re.match(r"(`{3,}|~{3,})", line)
        if marker:
            flush()
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        if fence:
            continue
        line = re.sub(r"`[^`]*`", "", line)
        if not line or re.match(r"^#{1,6}\s", line):
            flush()
            continue
        if line.startswith("|"):
            flush()
            if re.fullmatch(r"[|\s:\-]+", line):
                continue
            if index + 1 < len(lines) and re.fullmatch(r"[|\s:\-]+", lines[index + 1].strip()):
                continue  # table header
            units.append(line)
        elif re.match(r"^(?:[-+*]|\d+[.)])\s+", line):
            flush()
            units.append(re.sub(r"^(?:[-+*]|\d+[.)])\s+", "", line))
        else:
            paragraph.append(line)
    flush()
    return units


def validate_citations(report: str, evidence: list[Evidence]) -> CitationValidationResult:
    units = _text_units(report)
    text = "\n".join(units)
    ids = extract_citation_ids(text)
    known = {e.evidence_id for e in evidence if e.evidence_id}
    invalid = [i for i in ids if i not in known]
    malformed = list(dict.fromkeys(
        token for token in re.findall(r"\[[Ee][^\]\n]*\]", text)
        if not CITATION_PATTERN.fullmatch(token)
    ))
    warnings = [f"Unknown citation ID: {i}" for i in invalid]
    warnings.extend(f"Malformed citation: {token}" for token in malformed)
    if not ids:
        warnings.append("No body citations found; citation support was not checked.")
    claims = []
    for unit in units:
        evidence_ids = extract_citation_ids(unit)
        if evidence_ids:
            claims.append(CitationClaim(
                claim_id=f"C{len(claims) + 1}",
                claim=CITATION_PATTERN.sub("", unit).strip(), evidence_ids=evidence_ids,
            ))
    return CitationValidationResult(
        citation_ids=ids, valid_citation_ids=[i for i in ids if i in known],
        invalid_citation_ids=invalid, citation_count=len(CITATION_PATTERN.findall(text)),
        is_valid=not invalid and not malformed, warnings=warnings, claims=claims,
    )


def build_support_context(validation: CitationValidationResult, evidence: list[Evidence]) -> dict:
    lookup = {e.evidence_id: e for e in evidence if e.evidence_id}
    claims = []
    for claim in validation.claims:
        relevant = [lookup[i].model_dump() for i in claim.evidence_ids if i in lookup]
        claims.append(dict(claim.model_dump(), evidence=relevant, semantic_validation=bool(relevant)))
    # One batch within the existing Critic call. Uncited evidence is not sent
    # repeatedly with each claim. Legacy uncited reports keep general review.
    return {
        "citation_validation": validation.model_dump(), "claims": claims,
        "general_review_evidence": [e.model_dump() for e in evidence] if not validation.claims else [],
    }


def merge_citation_review(review: CriticReview, validation: CitationValidationResult) -> CriticReview:
    """Persist authoritative Python results and surface semantic findings.

    Missing/mismatched model checks are incomplete, never implicitly supported.
    Research decisions and queries remain the existing Critic's responsibility.
    """
    review = review.model_copy(deep=True)
    review.citation_validation = validation
    issues = []
    if not validation.is_valid:
        issues.append(CriticIssue(issue_type="invalid_citation",
                                 description="; ".join(validation.warnings),
                                 suggestion="Remove or correct citations using supplied Evidence IDs."))
    expected = {c.claim_id: c for c in validation.claims
                if any(i in validation.valid_citation_ids for i in c.evidence_ids)}
    accepted = {}
    for check in review.claim_support_checks:
        claim = expected.get(check.claim_id)
        if (claim is not None and check.claim == claim.claim
                and check.evidence_ids == claim.evidence_ids and check.claim_id not in accepted):
            accepted[check.claim_id] = check
        else:
            issues.append(CriticIssue(issue_type="citation_support_incomplete",
                                     description=f"Unexpected or mismatched support check: {check.claim_id}",
                                     suggestion="Review the supplied claim and its cited evidence."))
    review.claim_support_checks = list(accepted.values())
    for claim_id, claim in expected.items():
        check = accepted.get(claim_id)
        if check is None:
            issues.append(CriticIssue(issue_type="citation_support_incomplete",
                                     description=f"No support check returned for {claim_id}: {claim.claim}",
                                     suggestion="Evidence support remains unchecked; do not treat as supported."))
        elif check.status != "supported":
            issues.append(CriticIssue(issue_type=f"{check.status}_claim",
                                     description=f"{claim.claim} — {check.reason}",
                                     suggestion="Add supporting evidence, qualify, replace, or remove the claim."))
            gap = f"{claim.claim} — {check.reason}"
            if gap not in review.evidence_gaps:
                review.evidence_gaps.append(gap)
    for issue in issues:
        if issue not in review.issues:
            review.issues.append(issue)
    if issues and review.verdict == "PASS":
        review.verdict = "PASS_WITH_REVISIONS"
    return review
