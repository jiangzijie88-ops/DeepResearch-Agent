from models.evidence import Evidence
from workflow.citations import extract_citation_ids, append_references


def evidence(number, **kwargs):
    return Evidence(evidence_id=f"E{number}", title=f"Paper {number}",
                    evidence_type="paper", source="OpenAlex", summary="Summary", **kwargs)


def test_extract_unique_ids_in_first_appearance_order():
    assert extract_citation_ids("A [E2]. B [E5][E7]. C [E2][E12][E123] [E0] [E01]") == [
        "E2", "E5", "E7", "E12", "E123",
    ]


def test_references_only_use_cited_metadata_and_skip_missing_fields():
    result = append_references("Claim [E2][E5][E2].", [
        evidence(1), evidence(2, year=2025, authors=["Alice"], venue="Venue", doi="10.1/a"),
        evidence(5, url="https://example.invalid/paper"),
    ])
    refs = result.split("## References\n", 1)[1]
    assert "[E1]" not in refs
    assert refs.count("[E2]") == refs.count("[E5]") == 1
    for value in ["Paper 2", "2025", "Alice", "Venue", "10.1/a", "OpenAlex", "https://example.invalid/paper"]:
        assert value in refs
    for value in ["None", "null", "N/A"]:
        assert value not in refs


def test_unknown_citation_warns_without_fabricating_metadata(caplog):
    result = append_references("Unknown [E999]. Known [E1].", [evidence(1)])
    assert "E999" in caplog.text
    assert "[E999]" not in result.split("## References\n", 1)[1]
    assert "Unknown [E999]" in result


def test_references_replace_model_generated_section_and_are_idempotent():
    papers = [evidence(1)]
    result = append_references("Claim [E1].\n\n## References\n\n[E99] Invented metadata", papers)
    assert "Invented" not in result
    assert append_references(result, papers) == result
    assert result.count("## References") == 1


def test_no_citations_leaves_body_unchanged():
    assert append_references("No evidence available.", []) == "No evidence available."
