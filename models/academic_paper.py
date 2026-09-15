from pydantic import BaseModel, Field


class AcademicPaper(BaseModel):
    title: str

    authors: list[str] = Field(
        default_factory=list
    )

    year: int | None = None

    citations: int | None = None

    doi: str | None = None

    url: str | None = None

    venue: str | None = None

    published_at: str | None = None

    abstract: str | None = None

    source: str