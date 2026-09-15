from fastapi.testclient import TestClient

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