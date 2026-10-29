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


def test_paper_titles_get_links_without_changing_citation_ids_or_references():
    report = "## 论文清单\n\n- **Paper 1**：方法介绍 [E1]\n- Paper 2 [E2]\n- Paper 3 [E3]"
    papers = [evidence(1, doi="10.1000/demo"),
              evidence(2, url="https://example.org/paper(2)"), evidence(3)]
    result = append_references(report, papers)
    body, refs = result.split("## References", 1)
    assert "**[Paper 1](https://doi.org/10.1000/demo)**" in body
    assert "[Paper 2](https://example.org/paper%282%29)" in body
    assert "- Paper 3 [E3]" in body
    assert extract_citation_ids(body) == ["E1", "E2", "E3"]
    assert "[E1] Paper 1." in refs
    assert append_references(result, papers) == result


def test_title_links_use_stored_url_and_leave_existing_links_and_code_untouched():
    report = "[Paper 1](https://example.org/existing) [E1]\n`Paper 1`\nPaper 2 [E2]\nPaper 3 [E3]"
    papers = [evidence(1, url="https://example.org/one"),
              evidence(2, doi="https://doi.org/10.1000/two"),
              evidence(3, url="javascript:alert(1)")]
    body = append_references(report, papers).split("## References", 1)[0]
    assert "[Paper 1](https://example.org/existing)" in body
    assert "`Paper 1`" in body
    assert "[Paper 2](https://doi.org/10.1000/two)" in body
    assert "Paper 3 [E3]" in body
