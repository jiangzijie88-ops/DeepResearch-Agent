from models.research_state import ResearchState, ResearchStatus
from workflow.resume import ResumeStage, get_resume_stage


def test_initialized_resumes_from_planner():
    state = ResearchState(
        question="test",
        status=ResearchStatus.INITIALIZED,
    )

    assert get_resume_stage(state) == ResumeStage.PLANNER


def test_planned_resumes_from_research():
    state = ResearchState(
        question="test",
        status=ResearchStatus.PLANNED,
    )

    assert get_resume_stage(state) == ResumeStage.RESEARCH


def test_researching_restarts_research_stage():
    state = ResearchState(
        question="test",
        status=ResearchStatus.RESEARCHING,
    )

    assert get_resume_stage(state) == ResumeStage.RESEARCH


def test_writing_resumes_from_writer():
    state = ResearchState(
        question="test",
        status=ResearchStatus.WRITING,
    )

    assert get_resume_stage(state) == ResumeStage.WRITER


def test_reviewing_resumes_from_critic():
    state = ResearchState(
        question="test",
        status=ResearchStatus.REVIEWING,
    )

    assert get_resume_stage(state) == ResumeStage.CRITIC


def test_re_researching_resumes_from_research():
    state = ResearchState(
        question="test",
        status=ResearchStatus.RE_RESEARCHING,
    )

    assert get_resume_stage(state) == ResumeStage.RE_RESEARCH


def test_completed_state_is_done():
    state = ResearchState(
        question="test",
        status=ResearchStatus.COMPLETED,
    )

    assert get_resume_stage(state) == ResumeStage.DONE


def test_failed_state_resumes_from_planner_for_now():
    state = ResearchState(
        question="test",
        status=ResearchStatus.FAILED,
    )

    assert get_resume_stage(state) == ResumeStage.PLANNER


def test_resume_stage_has_revision_stage():
    assert ResumeStage.REVISION.value == "revision"


def test_resume_stage_has_final_critic_stage():
    assert ResumeStage.FINAL_CRITIC.value == "final_critic"

def test_revising_resumes_from_revision():
    state = ResearchState(
        question="test",
        status=ResearchStatus.REVISING,
    )

    assert get_resume_stage(state) == ResumeStage.REVISION


def test_final_reviewing_resumes_from_final_critic():
    state = ResearchState(
        question="test",
        status=ResearchStatus.FINAL_REVIEWING,
    )

    assert (
        get_resume_stage(state)
        == ResumeStage.FINAL_CRITIC
    )


def test_revising_skips_previous_stages():
    state = ResearchState(
        question="test",
        status=ResearchStatus.REVISING,
    )

    stage = get_resume_stage(
        state
    )

    assert stage != ResumeStage.PLANNER
    assert stage != ResumeStage.RESEARCH
    assert stage != ResumeStage.WRITER
    assert stage != ResumeStage.CRITIC
    assert stage != ResumeStage.RE_RESEARCH

    assert stage == ResumeStage.REVISION


def test_final_reviewing_skips_previous_stages():
    state = ResearchState(
        question="test",
        status=ResearchStatus.FINAL_REVIEWING,
    )

    stage = get_resume_stage(
        state
    )

    assert stage != ResumeStage.PLANNER
    assert stage != ResumeStage.RESEARCH
    assert stage != ResumeStage.WRITER
    assert stage != ResumeStage.CRITIC
    assert stage != ResumeStage.RE_RESEARCH
    assert stage != ResumeStage.REVISION

    assert stage == ResumeStage.FINAL_CRITIC