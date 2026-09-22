from fastapi.testclient import TestClient

from api.server import app


client = TestClient(app)



def test_stream_endpoint_exists(
    monkeypatch,
):


    def fake_pipeline(
        question,
        callback=None,
    ):

        if callback:

            callback(
                "Planner started"
            )

            callback(
                "Research completed"
            )


        class State:

            final_report = (
                "fake report"
            )

            draft_report = (
                "fake draft report"
            )


        return State()



    monkeypatch.setattr(
        "api.server.run_research_pipeline",
        fake_pipeline,
    )


    response = client.post(
        "/research/stream",
        json={
            "question":
            "test"
        }
    )


    assert response.status_code == 200


    text = response.text


    assert (
        "Planner started"
        in text
    )


    assert (
        "fake report"
        in text
    )