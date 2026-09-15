from models.academic_paper import AcademicPaper


def test_academic_paper_has_safe_defaults():
    paper = AcademicPaper(
        title="Test Paper",
        source="OpenAlex",
    )

    assert paper.title == "Test Paper"

    assert paper.source == "OpenAlex"

    assert paper.authors == []

    assert paper.year is None

    assert paper.citations is None

    assert paper.doi is None

    assert paper.url is None

    assert paper.venue is None

    assert paper.published_at is None

    assert paper.abstract is None


def test_academic_paper_accepts_full_metadata():
    paper = AcademicPaper(
        title="Multimodal Recommendation Paper",
        authors=[
            "Alice Zhang",
            "Bob Li",
        ],
        year=2025,
        citations=42,
        doi="10.1000/example",
        url="https://example.com/paper",
        venue="SIGIR",
        published_at="2025-07-15",
        abstract="A test abstract.",
        source="Semantic Scholar",
    )

    assert (
        paper.title
        == "Multimodal Recommendation Paper"
    )

    assert paper.authors == [
        "Alice Zhang",
        "Bob Li",
    ]

    assert paper.year == 2025

    assert paper.citations == 42

    assert (
        paper.doi
        == "10.1000/example"
    )

    assert (
        paper.url
        == "https://example.com/paper"
    )

    assert paper.venue == "SIGIR"

    assert (
        paper.published_at
        == "2025-07-15"
    )

    assert (
        paper.abstract
        == "A test abstract."
    )

    assert (
        paper.source
        == "Semantic Scholar"
    )