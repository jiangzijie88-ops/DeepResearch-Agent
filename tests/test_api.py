from fastapi.testclient import TestClient
import httpx
from openai import APIStatusError

from api.server import app

from models.research_state import (
    ResearchState,
)


client = TestClient(app)



def test_root():

    response = client.get("/")


    assert response.status_code == 200


    assert (
        response.json()["message"]
        ==
        "DeepResearch-Agent API running"
    )



def test_research_endpoint():

    response = client.post(
        "/research",
        json={
            "question":
            "test question"
        }
    )


    assert response.status_code == 200


    data = response.json()


    assert (
        data["question"]
        ==
        "test question"
    )


    assert (
        "report"
        in
        data
    )


    assert (
        "evidence_count"
        in
        data
    )

def test_research_endpoint(
    monkeypatch,
):


    from models.research_state import (
        ResearchState,
    )


    def fake_pipeline(
        question,
    ):


        state = ResearchState(
            question=question,
            draft_report="fake report",
        )


        state.evidence = []


        return state



    monkeypatch.setattr(
        "api.server.run_research_pipeline",
        fake_pipeline,
    )


    response = client.post(
        "/research",
        json={
            "question":
            "test question"
        }
    )


    assert response.status_code == 200


    data = response.json()


    assert (
        data["question"]
        ==
        "test question"
    )


    assert (
        data["report"]
        ==
        "fake report"
    )


def test_research_endpoint_reports_model_balance_error(monkeypatch):
    response = httpx.Response(
        402,
        request=httpx.Request("POST", "https://api.deepseek.com/chat/completions"),
    )

    def insufficient_balance(question):
        raise APIStatusError("Insufficient Balance", response=response, body=None)

    monkeypatch.setattr("api.server.run_research_pipeline", insufficient_balance)

    result = client.post("/research", json={"question": "test question"})

    assert result.status_code == 402
    assert result.json()["detail"] == "模型账户余额不足，请充值或更换 API 密钥。"
