import pytest
from pydantic import ValidationError

from models.evidence import Evidence


def test_evidence_new_fields_have_safe_defaults():
    evidence = Evidence(
        title="Test Paper",
        evidence_type="paper",
        year=2025,
        citations=10,
        source="OpenAlex",
        doi="10.1000/test",
        url="https://example.com/test",
        summary="测试 Evidence。",
        verified=True,
    )

    assert evidence.authors == []
    assert evidence.venue is None
    assert evidence.published_at is None
    assert evidence.retrieved_at is None
    assert evidence.query is None
    assert evidence.confidence is None


def test_evidence_accepts_extended_metadata():
    evidence = Evidence(
        title="Extended Paper",
        evidence_type="paper",
        year=2025,
        citations=25,
        source="OpenAlex",
        doi="10.1000/extended",
        url="https://example.com/extended",
        summary="包含完整扩展字段的测试 Evidence。",
        verified=True,
        authors=[
            "Alice Zhang",
            "Bob Li",
        ],
        venue="SIGIR",
        published_at="2025-07-15",
        retrieved_at="2026-08-31T10:30:00",
        query="multimodal recommendation GNN",
        confidence=0.92,
    )

    assert evidence.authors == [
        "Alice Zhang",
        "Bob Li",
    ]

    assert evidence.venue == "SIGIR"
    assert evidence.published_at == "2025-07-15"
    assert evidence.retrieved_at == "2026-08-31T10:30:00"

    assert (
        evidence.query
        == "multimodal recommendation GNN"
    )

    assert evidence.confidence == 0.92


def test_evidence_confidence_cannot_be_less_than_zero():
    with pytest.raises(
        ValidationError
    ):
        Evidence(
            title="Invalid Confidence",
            evidence_type="paper",
            year=2025,
            citations=0,
            source="OpenAlex",
            doi=None,
            url=None,
            summary="confidence 小于 0。",
            verified=False,
            confidence=-0.1,
        )


def test_evidence_confidence_cannot_be_greater_than_one():
    with pytest.raises(
        ValidationError
    ):
        Evidence(
            title="Invalid Confidence",
            evidence_type="paper",
            year=2025,
            citations=0,
            source="OpenAlex",
            doi=None,
            url=None,
            summary="confidence 大于 1。",
            verified=False,
            confidence=1.1,
        )


def test_old_evidence_data_remains_compatible():
    old_data = {
        "title": "Legacy Paper",
        "evidence_type": "paper",
        "year": 2024,
        "citations": 5,
        "source": "OpenAlex",
        "doi": None,
        "url": "https://example.com/legacy",
        "summary": "旧版本 Evidence。",
        "verified": True,
    }

    evidence = Evidence.model_validate(
        old_data
    )

    assert evidence.title == "Legacy Paper"

    assert evidence.authors == []
    assert evidence.venue is None
    assert evidence.published_at is None
    assert evidence.retrieved_at is None
    assert evidence.query is None
    assert evidence.confidence is None