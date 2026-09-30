from pathlib import Path

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse
from api.streaming import stream_events

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
    except APITimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail="模型服务响应超时，请稍后重试。",
        ) from error
    except APIConnectionError as error:
        raise HTTPException(
            status_code=502,
            detail="模型服务连接中断，请检查后端网络或代理后重试。",
        ) from error
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
def research_stream(request: ResearchRequest):
    return StreamingResponse(
        stream_events(lambda on_event: run_research_pipeline(
            request.question, memory_path=MEMORY_PATH, on_event=on_event,
        )),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
