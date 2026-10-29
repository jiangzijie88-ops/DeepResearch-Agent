from pathlib import Path

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse
from api.streaming import stream_events

from workflow.pipeline import (
    run_research_pipeline,
)


MEMORY_PATH = Path(__file__).resolve().parents[1] / "outputs" / "memory.json"
REPORT_DIR = MEMORY_PATH.parent


def run_and_save_report(question: str, *, on_event=None):
    """Persist the displayed report before returning a successful API result."""
    kwargs = {"memory_path": MEMORY_PATH}
    if on_event is not None:
        kwargs["on_event"] = on_event
    state = run_research_pipeline(question, **kwargs)
    report = state.final_report or state.draft_report
    if report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = REPORT_DIR / f"report_{timestamp}_{uuid4().hex[:12]}.md"
        path.write_text(report, encoding="utf-8")
    return state


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
        state = run_and_save_report(
            request.question,
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
        stream_events(lambda on_event: run_and_save_report(
            request.question, on_event=on_event,
        )),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
