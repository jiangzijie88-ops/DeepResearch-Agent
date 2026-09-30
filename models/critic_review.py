from pydantic import BaseModel, Field
from typing import Literal


class CitationClaim(BaseModel):
    claim_id: str
    claim: str
    evidence_ids: list[str]


class CitationValidationResult(BaseModel):
    citation_ids: list[str] = Field(default_factory=list)
    valid_citation_ids: list[str] = Field(default_factory=list)
    invalid_citation_ids: list[str] = Field(default_factory=list)
    citation_count: int = 0
    is_valid: bool = True
    warnings: list[str] = Field(default_factory=list)
    claims: list[CitationClaim] = Field(default_factory=list)


class ClaimSupportCheck(CitationClaim):
    status: Literal["supported", "partially_supported", "unsupported"]
    reason: str


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
    citation_validation: CitationValidationResult | None = None
    claim_support_checks: list[ClaimSupportCheck] = Field(default_factory=list)

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
