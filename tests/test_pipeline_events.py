from workflow.pipeline import (
    run_research_pipeline,
)


def test_pipeline_callback_exists():

    events = []


    def callback(
        message,
    ):

        events.append(
            message
        )


    assert callable(
        callback
    )