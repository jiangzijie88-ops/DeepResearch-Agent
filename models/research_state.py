from enum import Enum

from pydantic import BaseModel, Field

from models.evidence import Evidence
from models.critic_review import CriticReview
from workers.planner import ResearchPlan


class ResearchStatus(str, Enum):
    INITIALIZED = "initialized"
    PLANNED = "planned"
    RESEARCHING = "researching"
    WRITING = "writing"
    REVIEWING = "reviewing"
    RE_RESEARCHING = "re_researching"
    REVISING = "revising"
    FINAL_REVIEWING = "final_reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchState(BaseModel):
    """
    DeepResearch workflow 的统一状态对象。

    当前版本只负责保存状态，
    暂不负责持久化、恢复或 workflow 调度。
    """

    question: str

    plan: ResearchPlan | None = None

    tool_routes: dict[str, list[str]] = Field(default_factory=dict)

    evidence: list[Evidence] = Field(
        default_factory=list
    )

    draft_report: str | None = None

    critic_review: CriticReview | None = None

    research_round: int = 0

    status: ResearchStatus = ResearchStatus.INITIALIZED

    final_report: str | None = None

    final_review: CriticReview | None = None
