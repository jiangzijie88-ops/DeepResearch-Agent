from workflow.pipeline import (
    run_research_pipeline,
)


def test_pipeline_function_exists():

    assert callable(
        run_research_pipeline
    )