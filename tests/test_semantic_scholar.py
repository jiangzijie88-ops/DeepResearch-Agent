import pytest
import requests

from models.academic_paper import AcademicPaper

from tools.academic.semantic_scholar import (
    parse_semantic_scholar_paper,
    search_semantic_scholar,
)


def test_parse_semantic_scholar_paper_maps_metadata():
    raw_paper = {
        "paperId": "s2-test-id",

        "title": (
            "Test Semantic Scholar Paper"
        ),

        "year": 2025,

        "citationCount": 35,

        "url": (
            "https://www.semanticscholar.org/"
            "paper/s2-test-id"
        ),

        "venue": "SIGIR",

        "publicationDate": (
            "2025-07-15"
        ),

        "abstract": (
            "This is a test abstract."
        ),

        "authors": [
            {
                "authorId": "1",
                "name": "Alice Zhang",
            },
            {
                "authorId": "2",
                "name": "Bob Li",
            },
        ],

        "externalIds": {
            "DOI": "10.1000/s2-test"
        },
    }

    paper = (
        parse_semantic_scholar_paper(
            raw_paper
        )
    )

    assert isinstance(
        paper,
        AcademicPaper,
    )

    assert (
        paper.title
        == "Test Semantic Scholar Paper"
    )

    assert paper.authors == [
        "Alice Zhang",
        "Bob Li",
    ]

    assert paper.year == 2025

    assert paper.citations == 35

    assert (
        paper.doi
        == "10.1000/s2-test"
    )

    assert (
        paper.url
        == (
            "https://www.semanticscholar.org/"
            "paper/s2-test-id"
        )
    )

    assert paper.venue == "SIGIR"

    assert (
        paper.published_at
        == "2025-07-15"
    )

    assert (
        paper.abstract
        == "This is a test abstract."
    )

    assert (
        paper.source
        == "Semantic Scholar"
    )


def test_parse_semantic_scholar_paper_handles_missing_metadata():
    raw_paper = {
        "paperId": "incomplete-id",
        "title": "Incomplete Paper",
        "year": 2024,
        "authors": None,
        "externalIds": None,
    }

    paper = (
        parse_semantic_scholar_paper(
            raw_paper
        )
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

    assert (
        paper.source
        == "Semantic Scholar"
    )


class FakeSemanticScholarResponse:

    status_code = 200

    def json(
        self,
    ):
        return {
            "total": 1,

            "data": [
                {
                    "paperId": "api-paper",

                    "title": (
                        "Semantic Scholar "
                        "API Test Paper"
                    ),

                    "year": 2025,

                    "citationCount": 18,

                    "url": (
                        "https://www."
                        "semanticscholar.org/"
                        "paper/api-paper"
                    ),

                    "venue": "AAAI",

                    "publicationDate": (
                        "2025-03-10"
                    ),

                    "abstract": (
                        "API test abstract."
                    ),

                    "authors": [
                        {
                            "authorId": "1",
                            "name": (
                                "Alice Zhang"
                            ),
                        }
                    ],

                    "externalIds": {
                        "DOI": (
                            "10.1000/"
                            "semantic-api"
                        )
                    },
                }
            ],
        }


class FakeSemanticScholarGet:

    def __init__(
        self,
    ):
        self.url = None
        self.params = None
        self.headers = None
        self.timeout = None

    def __call__(
        self,
        url,
        params,
        headers,
        timeout,
    ):
        self.url = url
        self.params = params
        self.headers = headers
        self.timeout = timeout

        return (
            FakeSemanticScholarResponse()
        )


def test_search_semantic_scholar_builds_request_and_returns_papers():
    fake_get = (
        FakeSemanticScholarGet()
    )

    papers = search_semantic_scholar(
        query=(
            "multimodal recommendation"
        ),
        year_start=2024,
        year_end=2026,
        limit=5,
        api_key="test-key",
        request_get=fake_get,
    )

    assert len(papers) == 1

    assert (
        papers[0].title
        == (
            "Semantic Scholar "
            "API Test Paper"
        )
    )

    assert (
        fake_get.url
        == (
            "https://api."
            "semanticscholar.org/"
            "graph/v1/paper/search"
        )
    )

    assert (
        fake_get.params["query"]
        == "multimodal recommendation"
    )

    assert (
        fake_get.params["year"]
        == "2024-2026"
    )

    assert (
        fake_get.params["limit"]
        == 5
    )

    assert (
        fake_get.headers[
            "x-api-key"
        ]
        == "test-key"
    )

    assert fake_get.timeout == 15

    fields = (
        fake_get.params["fields"]
    )

    assert "title" in fields

    assert "authors" in fields

    assert "year" in fields

    assert "citationCount" in fields

    assert "externalIds" in fields

    assert "url" in fields

    assert "venue" in fields

    assert "publicationDate" in fields

    assert "abstract" in fields

class FakeSemanticScholarRateLimitResponse:

    status_code = 429

    def json(
        self,
    ):
        return {}


class FakeSemanticScholarRetryGet:

    def __init__(
        self,
    ):
        self.calls = 0

    def __call__(
        self,
        url,
        params,
        headers,
        timeout,
    ):
        self.calls += 1

        if self.calls < 3:

            return (
                FakeSemanticScholarRateLimitResponse()
            )

        return (
            FakeSemanticScholarResponse()
        )


class FakeSemanticScholarSleep:

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


def test_search_semantic_scholar_retries_rate_limit_with_backoff():
    fake_get = (
        FakeSemanticScholarRetryGet()
    )

    fake_sleep = (
        FakeSemanticScholarSleep()
    )

    papers = search_semantic_scholar(
        query="retry test",
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



class FakeSemanticScholarAlwaysRateLimitedGet:

    def __init__(
        self,
    ):
        self.calls = 0

    def __call__(
        self,
        url,
        params,
        headers,
        timeout,
    ):
        self.calls += 1

        return (
            FakeSemanticScholarRateLimitResponse()
        )


def test_search_semantic_scholar_raises_after_max_rate_limit_retries():
    fake_get = (
        FakeSemanticScholarAlwaysRateLimitedGet()
    )

    fake_sleep = (
        FakeSemanticScholarSleep()
    )

    with pytest.raises(
        RuntimeError,
        match="rate limit",
    ):
        search_semantic_scholar(
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


def test_search_semantic_scholar_works_without_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        "SEMANTIC_SCHOLAR_API_KEY",
        raising=False,
    )

    fake_get = (
        FakeSemanticScholarGet()
    )

    papers = search_semantic_scholar(
        query="public test",
        api_key=None,
        request_get=fake_get,
    )

    assert len(papers) == 1

    assert fake_get.headers == {}


class FakeSemanticScholarServerErrorResponse:

    status_code = 500

    def json(
        self,
    ):
        return {}


class FakeSemanticScholarServerErrorGet:

    def __call__(
        self,
        url,
        params,
        headers,
        timeout,
    ):
        return (
            FakeSemanticScholarServerErrorResponse()
        )


def test_search_semantic_scholar_raises_on_http_error():
    with pytest.raises(
        RuntimeError,
        match="HTTP status 500",
    ):
        search_semantic_scholar(
            query="server error",
            request_get=(
                FakeSemanticScholarServerErrorGet()
            ),
            api_key="test-key",
        )


class FakeSemanticScholarTimeoutGet:

    def __call__(
        self,
        url,
        params,
        headers,
        timeout,
    ):
        raise requests.Timeout(
            "test timeout"
        )



def test_search_semantic_scholar_wraps_network_error():
    with pytest.raises(
        RuntimeError,
        match="network error",
    ):
        search_semantic_scholar(
            query="timeout test",
            request_get=(
                FakeSemanticScholarTimeoutGet()
            ),
            api_key="test-key",
        )