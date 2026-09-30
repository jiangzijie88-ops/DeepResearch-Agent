import pytest

from models.evidence import Evidence
from models.critic_review import CriticReview, ClaimSupportCheck
from workflow.citation_validation import validate_citations, build_support_context, merge_citation_review


def evidence(number, summary="Proposes graph retrieval."):
    return Evidence(evidence_id=f"E{number}", title=f"Paper {number}", summary=summary,
                    source="OpenAlex", evidence_type="paper")


def review(**kwargs):
    return CriticReview(overall_assessment="Review", issues=[], evidence_gaps=[],
                        needs_research=False, research_queries=[], verdict="PASS", **kwargs)


def test_existence_ignores_references_and_counts_body_occurrences():
    result = validate_citations("A [E1]. B [E1][E999].\n\n## References\n[E2] Paper", [evidence(1), evidence(2)])
    assert result.citation_ids == ["E1", "E999"]
    assert result.valid_citation_ids == ["E1"]
    assert result.invalid_citation_ids == ["E999"]
    assert result.citation_count == 3
    assert not result.is_valid


@pytest.mark.parametrize("citation", ["[E 1]", "[e1]", "[E-1]", "[Eabc]", "[E0]", "[E01]"])
def test_malformed_citations_warn_without_crashing(citation):
    result = validate_citations(f"Claim {citation}.", [evidence(1)])
    assert result.citation_ids == []
    assert not result.is_valid
    assert result.warnings


def test_common_markdown_claim_units_and_wrapped_paragraphs():
    report = """## Heading [E9]
下面介绍方法。

Method A works [E1]. Method B works [E2][E3].

- A bullet [E1].
1. A numbered item [E2].

| Method | Evidence |
| --- | --- |
| GraphRAG | [E3] |

A wrapped
claim [E1].

```text
Example [E999]
```
"""
    result = validate_citations(report, [evidence(i) for i in range(1, 4)])
    assert [c.evidence_ids for c in result.claims] == [["E1"], ["E2", "E3"], ["E1"], ["E2"], ["E3"], ["E1"]]
    assert result.claims[-1].claim == "A wrapped claim ."
    assert result.is_valid


def test_context_only_contains_claims_referenced_evidence_and_skips_missing():
    result = validate_citations("Joint claim [E1][E2][E3]. Missing [E999].", [evidence(i) for i in range(1, 5)])
    context = build_support_context(result, [evidence(i) for i in range(1, 5)])
    assert [e["evidence_id"] for e in context["claims"][0]["evidence"]] == ["E1", "E2", "E3"]
    assert context["claims"][1]["semantic_validation"] is False
    assert context["claims"][1]["evidence"] == []
    assert "Paper 4" not in str(context)


@pytest.mark.parametrize("status", ["supported", "partially_supported", "unsupported"])
def test_semantic_results_preserved_and_issues_integrated(status):
    validation = validate_citations("Accuracy improves 35% [E1].", [evidence(1)])
    claim = validation.claims[0]
    check = ClaimSupportCheck(claim_id=claim.claim_id, claim=claim.claim, evidence_ids=["E1"],
                              status=status, reason="Evidence contains no measured percentage.")
    result = merge_citation_review(review(claim_support_checks=[check]), validation)
    assert result.claim_support_checks[0].status == status
    if status != "supported":
        assert result.issues and result.evidence_gaps
        assert result.verdict != "PASS"
    assert result.citation_validation == validation


def test_missing_checks_and_invalid_ids_cannot_silently_pass():
    validation = validate_citations("Known [E1]. Unknown [E999].", [evidence(1)])
    result = merge_citation_review(review(), validation)
    assert result.verdict != "PASS"
    assert {i.issue_type for i in result.issues} >= {"invalid_citation", "citation_support_incomplete"}
    assert not result.needs_research  # No fabricated research queries.


def test_empty_citations_are_a_warning_and_legacy_review_loads():
    validation = validate_citations("下面介绍方法。", [])
    assert validation.is_valid and validation.warnings and not validation.claims
    old = review().model_dump(exclude={"citation_validation", "claim_support_checks"})
    restored = CriticReview.model_validate(old)
    assert restored.citation_validation is None and restored.claim_support_checks == []
