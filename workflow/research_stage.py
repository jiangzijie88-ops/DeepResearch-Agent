from models.evidence import Evidence
from workers.planner import ResearchPlan

from workflow.stages import (
    run_research_query,
)



def run_research_stage(
    plan: ResearchPlan,
    runner=None,
):

    all_evidence: list[Evidence] = []


    for sub_question in (
        plan.sub_questions
    ):

        evidence_list = (
            run_research_query(
                query=sub_question.question,

                search_type=(
                    sub_question.search_type
                ),

                runner=runner,
            )
        )


        all_evidence.extend(
            evidence_list
        )


    return all_evidence