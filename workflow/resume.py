from enum import Enum

from models.research_state import ResearchState, ResearchStatus


class ResumeStage(str, Enum):
    PLANNER = "planner"
    RESEARCH = "research"
    WRITER = "writer"
    CRITIC = "critic"
    RE_RESEARCH = "re_research"
    REVISION = "revision"
    FINAL_CRITIC = "final_critic"
    DONE = "done"


def get_resume_stage(
    state: ResearchState,
) -> ResumeStage:

    mapping = {
        ResearchStatus.INITIALIZED: ResumeStage.PLANNER,
        ResearchStatus.PLANNED: ResumeStage.RESEARCH,
        ResearchStatus.RESEARCHING: ResumeStage.RESEARCH,
        ResearchStatus.WRITING: ResumeStage.WRITER,
        ResearchStatus.REVIEWING: ResumeStage.CRITIC,
        ResearchStatus.RE_RESEARCHING: ResumeStage.RE_RESEARCH,
        ResearchStatus.REVISING: ResumeStage.REVISION,
        ResearchStatus.FINAL_REVIEWING: ResumeStage.FINAL_CRITIC,
        ResearchStatus.COMPLETED: ResumeStage.DONE,
        ResearchStatus.FAILED: ResumeStage.PLANNER,
    }

    return mapping[state.status]