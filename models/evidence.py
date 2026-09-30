from pydantic import BaseModel, Field


class Evidence(BaseModel):
    evidence_id: str | None = Field(default=None, pattern=r"^E[1-9][0-9]*$")
    title: str
    evidence_type: str

    year: int | None = None
    citations: int | None = None

    source: str

    doi: str | None = None
    url: str | None = None

    summary: str

    verified: bool = False

    # ========================================================
    # Extended Metadata
    # ========================================================

    authors: list[str] = Field(
        default_factory=list
    )

    venue: str | None = None

    published_at: str | None = None

    retrieved_at: str | None = None

    query: str | None = None

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
