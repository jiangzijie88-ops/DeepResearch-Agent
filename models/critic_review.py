from pydantic import BaseModel, Field


class CriticIssue(BaseModel):

    issue_type: str = Field(
        description="问题类型，例如 unsupported_claim、scope_error、missing_evidence"
    )

    description: str = Field(
        description="发现的问题"
    )

    suggestion: str = Field(
        description="建议如何修改"
    )


class CriticReview(BaseModel):

    overall_assessment: str = Field(
        description="对报告整体质量的评价"
    )

    issues: list[CriticIssue] = Field(
        description="发现的问题列表"
    )

    evidence_gaps: list[str] = Field(
        description="当前证据仍然缺失的内容"
    )

    needs_research: bool = Field(
        description="是否需要补充搜索"
    )

    research_queries: list[str] = Field(
        description="如果需要补搜，应执行的具体研究问题"
    )

    verdict: str = Field(
        description="审核结论，只能是 PASS、PASS_WITH_REVISIONS 或 FAIL"
    )