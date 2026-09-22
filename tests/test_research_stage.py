from models.search_type import (
    SearchType,
)

from workers.planner import (
    ResearchPlan,
    ResearchSubQuestion,
)

from workflow.stages import (
    run_research_stage,
)


class FakeEvidence:

    def __init__(self, title):
        self.title = title



def test_research_stage_accepts_plan():

    plan = ResearchPlan(
        research_goal="test",

        sub_questions=[

            ResearchSubQuestion(
                id=1,
                question="paper search test",
                search_type=(
                    SearchType.PAPER_SEARCH
                ),
            )
        ],
    )


    assert len(
        plan.sub_questions
    ) == 1



def test_research_stage_calls_each_sub_question(
    monkeypatch,
):

    called_queries = []


    def fake_run_research_query(
        query,
        search_type=None,
        runner=None,
    ):

        called_queries.append(
            (
                query,
                search_type,
            )
        )


        return [
            FakeEvidence(
                "test paper"
            )
        ]


    monkeypatch.setattr(
        "workflow.stages.run_research_query",
        fake_run_research_query,
    )


    plan = ResearchPlan(
        research_goal="test",

        sub_questions=[

            ResearchSubQuestion(
                id=1,
                question="find papers",

                search_type=(
                    SearchType.PAPER_SEARCH
                ),
            ),

            ResearchSubQuestion(
                id=2,
                question="find website",

                search_type=(
                    SearchType.WEB_SEARCH
                ),
            ),
        ],
    )


    evidence = run_research_stage(
        plan
    )


    assert len(
        evidence
    ) == 2


    assert called_queries == [

        (
            "find papers",
            SearchType.PAPER_SEARCH,
        ),

        (
            "find website",
            SearchType.WEB_SEARCH,
        ),

    ]