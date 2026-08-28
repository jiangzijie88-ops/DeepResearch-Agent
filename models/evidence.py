from typing import Optional
from pydantic import BaseModel, Field


class Evidence(BaseModel):

    title: str = Field(
        description="证据对应的论文、网页或资料标题"
    )

    evidence_type: str = Field(
        description="证据类型，例如 paper、web"
    )

    year: Optional[int] = Field(
        default=None,
        description="发表或发布时间"
    )

    citations: Optional[int] = Field(
        default=None,
        description="论文引用量；如果无法验证则为 None"
    )

    source: str = Field(
        description="证据来源，例如 OpenAlex、Web Search"
    )

    doi: Optional[str] = Field(
        default=None,
        description="论文 DOI"
    )

    url: Optional[str] = Field(
        default=None,
        description="证据 URL"
    )

    summary: str = Field(
        description="这条证据与当前研究问题相关的核心内容"
    )

    verified: bool = Field(
        description="该证据是否经过可信数据源验证"
    )