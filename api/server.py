import json

from fastapi import FastAPI
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse

from workflow.pipeline import (
    run_research_pipeline,
)


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


    state = run_research_pipeline(
        request.question
    )


    return ResearchResponse(

      question=(
          state.question
      ),


      status=(
          state.status.value
      ),


      report=(
          state.draft_report
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
                    "final_report":
                    state.draft_report
                    or ""
                },
                ensure_ascii=False,
            )
            + "\n"
        )


    return StreamingResponse(
        event_generator(),
        media_type="application/json",
    )
