from datetime import datetime

from pydantic import BaseModel, Field



class MemoryItem(BaseModel):

    """
    Long-term memory record.

    Stores completed research experience.
    """


    question: str


    summary: str = ""


    evidence_count: int = 0


    created_at: str = Field(
        default_factory=lambda:
        datetime.utcnow()
        .isoformat(
            timespec="seconds"
        )
    )