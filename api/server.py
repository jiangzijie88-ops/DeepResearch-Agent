import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from openai import APIStatusError
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse

from workflow.pipeline import (
    run_research_pipeline,
)


MEMORY_PATH = Path(__file__).resolve().parents[1] / "outputs" / "memory.json"


app = FastAPI(
    title="DeepResearch-Agent API",
    description="Multi-Agent Research Assistant",
    version="1.0",
)


class ResearchRequest(BaseModel):

    question: str



class ResearchResponse(BaseModel):

    question: str

    status: str

    report: str

    evidence_count: int

    evidence: list = Field(default_factory=list)



@app.get("/")
def root():

    return {
        "message":
        "DeepResearch-Agent API running"
    }



@app.post(
    "/research",
    response_model=ResearchResponse,
)
def research(
    request: ResearchRequest,
):
    try:
        state = run_research_pipeline(
            request.question,
            memory_path=MEMORY_PATH,
        )
    except APIStatusError as error:
        if error.status_code == 402:
            raise HTTPException(
                status_code=402,
                detail="模型账户余额不足，请充值或更换 API 密钥。",
            ) from error
        raise


    return ResearchResponse(

      question=(
          state.question
      ),


      status=(
          state.status.value
      ),


      report=(
        state.final_report
        or state.draft_report
        or "No report generated."
      ),


      evidence_count=(
          len(state.evidence)
      ),


      evidence=[
          item.model_dump()
          for item in state.evidence
      ],

  )


@app.post("/research/stream")
def research_stream(
    request: ResearchRequest,
):


    def event_generator():

        events = []


        def callback(
            message,
        ):

            events.append(
                message
            )


        state = run_research_pipeline(
            request.question,
            callback=callback,
            memory_path=MEMORY_PATH,
        )


        for event in events:

            yield (
                json.dumps(
                    {
                        "event": event
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


        yield (
            json.dumps(
                {
                    "final_report": (
                        state.final_report
                        or state.draft_report
                        or ""
                    )
                },
                ensure_ascii=False,
            )
            + "\n"
        )


    return StreamingResponse(
        event_generator(),
        media_type="application/json",
    )
