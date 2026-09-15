import pytest
import requests

from models.academic_paper import AcademicPaper

from tools.academic.openalex import (
    parse_openalex_work,
    search_openalex,
)


def test_parse_openalex_work_maps_metadata():
    work = {
        "title": "Test OpenAlex Paper",

        "publication_year": 2025,

        "abstract_inverted_index": {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3],
            "abstract": [4],
            ".": [5],
        },

        "publication_date": "2025-07-15",

        "cited_by_count": 42,

        "doi": (
            "https://doi.org/"
            "10.1000/openalex-test"
        ),

        "authorships": [
            {
                "author": {
                    "display_name": (
                        "Alice Zhang"
                    )
                }
            },
            {
                "author": {
                    "display_name": (
                        "Bob Li"
                    )
                }
            },
        ],

        "primary_location": {
            "landing_page_url": (
                "https://example.com/paper"
            ),
            "source": {
                "display_name": "SIGIR"
            },
        },
    }

    paper = parse_openalex_work(
        work
    )

    assert isinstance(
        paper,
        AcademicPaper,
    )

    assert (
        paper.title
        == "Test OpenAlex Paper"
    )

    assert paper.authors == [
        "Alice Zhang",
        "Bob Li",
    ]

    assert paper.year == 2025

    assert paper.citations == 42

    assert (
        paper.doi
        == (
            "https://doi.org/"
            "10.1000/openalex-test"
        )
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

    assert paper.source == "OpenAlex"

    assert (
        paper.abstract
        == "This is a test abstract ."
    )


def test_parse_openalex_work_handles_missing_metadata():
    work = {
        "title": "Incomplete Paper",
        "publication_year": 2024,
        "authorships": [],
        "primary_location": None,
    }

    paper = parse_openalex_work(
        work
    )

    assert (
        paper.title
        == "Incomplete Paper"
    )

    assert paper.authors == []

    assert paper.year == 2024

    assert paper.citations is None

    assert paper.doi is None

    assert paper.url is None

    assert paper.venue is None

    assert paper.published_at is None

    assert paper.abstract is None

    assert paper.source == "OpenAlex"

class FakeOpenAlexResponse:

    status_code = 200

    def raise_for_status(
        self,
    ):
        return None

    def json(
        self,
    ):
        return {
            "results": [
                {
                    "title": (
                        "API Test Paper"
                    ),

                    "publication_year": 2025,

                    "publication_date": (
                        "2025-05-01"
                    ),

                    "cited_by_count": 7,

                    "doi": (
                        "https://doi.org/"
                        "10.1000/api-test"
                    ),

                    "authorships": [],

                    "primary_location": {
                        "landing_page_url": (
                            "https://example.com/"
                            "api-test"
                        ),

                        "source": {
                            "display_name": (
                                "Test Venue"
                            )
                        },
                    },
                }
            ]
        }

class FakeOpenAlexGet:

    def __init__(
        self,
    ):
        self.url = None
        self.params = None
        self.timeout = None

    def __call__(
        self,
        url,
        params,
        timeout,
    ):
        self.url = url
        self.params = params
        self.timeout = timeout

        return FakeOpenAlexResponse()


def test_search_openalex_builds_request_and_returns_papers():
    fake_get = FakeOpenAlexGet()

    papers = search_openalex(
        query=(
            "multimodal recommendation"
        ),
        year_start=2024,
        year_end=2026,
        per_page=5,
        api_key="test-key",
        request_get=fake_get,
    )

    assert len(papers) == 1

    assert (
        papers[0].title
        == "API Test Paper"
    )

    assert (
        fake_get.url
        == "https://api.openalex.org/works"
    )

    assert (
        fake_get.params["search"]
        == "multimodal recommendation"
    )

    assert (
        fake_get.params["filter"]
        == (
            "from_publication_date:"
            "2024-01-01,"
            "to_publication_date:"
            "2026-12-31"
        )
    )

    assert (
        fake_get.params["per_page"]
        == 5
    )

    assert (
        fake_get.params["api_key"]
        == "test-key"
    )

    assert fake_get.timeout == 15


class FakeRateLimitResponse:

    status_code = 429

    def json(
        self,
    ):
        return {}


class FakeRetryGet:

    def __init__(
        self,
    ):
        self.calls = 0

    def __call__(
        self,
        url,
        params,
        timeout,
    ):
        self.calls += 1

        if self.calls < 3:
            return (
                FakeRateLimitResponse()
            )

        return FakeOpenAlexResponse()


class FakeSleep:

    def __init__(
        self,
    ):
        self.delays = []

    def __call__(
        self,
        seconds,
    ):
        self.delays.append(
            seconds
        )


def test_search_openalex_retries_rate_limit_with_backoff():
    fake_get = FakeRetryGet()

    fake_sleep = FakeSleep()

    papers = search_openalex(
        query="retry test",
        year_start=2024,
        year_end=2026,
        request_get=fake_get,
        sleep=fake_sleep,
        api_key="test-key",
    )

    assert fake_get.calls == 3

    assert fake_sleep.delays == [
        1,
        2,
    ]

    assert len(papers) == 1


class FakeAlwaysRateLimitedGet:

    def __init__(
        self,
    ):
        self.calls = 0

    def __call__(
        self,
        url,
        params,
        timeout,
    ):
        self.calls += 1

        return (
            FakeRateLimitResponse()
        )


def test_search_openalex_raises_after_max_rate_limit_retries():
    fake_get = (
        FakeAlwaysRateLimitedGet()
    )

    fake_sleep = FakeSleep()

    with pytest.raises(
        RuntimeError,
        match="rate limit",
    ):
        search_openalex(
            query="always limited",
            request_get=fake_get,
            sleep=fake_sleep,
            api_key="test-key",
            max_attempts=3,
        )

    assert fake_get.calls == 3

    assert fake_sleep.delays == [
        1,
        2,
    ]


def test_search_openalex_works_without_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        "OPENALEX_API_KEY",
        raising=False,
    )

    fake_get = FakeOpenAlexGet()

    papers = search_openalex(
        query="public api test",
        request_get=fake_get,
        api_key=None,
    )

    assert len(papers) == 1

    assert (
        "api_key"
        not in fake_get.params
    )


class FakeOpenAlexTimeoutGet:

    def __call__(
        self,
        url,
        params,
        timeout,
    ):
        raise requests.Timeout(
            "test timeout"
        )


def test_search_openalex_wraps_network_error():
    with pytest.raises(
        RuntimeError,
        match="network error",
    ):
        search_openalex(
            query="timeout test",
            request_get=(
                FakeOpenAlexTimeoutGet()
            ),
            api_key="test-key",
        )