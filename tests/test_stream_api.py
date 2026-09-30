import asyncio
import json
from threading import Event

from fastapi.testclient import TestClient
from api.server import app
from models.research_state import ResearchState
from workflow.events import WorkflowEvent


def event(message):
    return WorkflowEvent(type="stage_started", stage="planner", message=message)


def parse_frames(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_stream_endpoint_exists(monkeypatch):
    def fake(question, *, memory_path, on_event):
        on_event(event("正在生成研究计划"))
        return ResearchState(question=question, final_report="fake report")
    monkeypatch.setattr("api.server.run_research_pipeline", fake)
    response = TestClient(app).post("/research/stream", json={"question": "test"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.text.endswith("\n\n")
    events = parse_frames(response.text)
    assert events[0]["message"] == "正在生成研究计划"
    assert events[-1]["type"] == "workflow_completed"
    assert events[-1]["data"]["report"] == "fake report"
    assert sum(e["type"] == "workflow_completed" for e in events) == 1


async def asgi_request(question, on_chunk):
    body = json.dumps({"question": question}).encode()
    requested = False
    async def receive():
        nonlocal requested
        if not requested:
            requested = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.Event().wait()
    async def send(message):
        if message["type"] == "http.response.body" and message.get("body"):
            on_chunk(message["body"].decode())
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
             "http_version": "1.1", "method": "POST", "scheme": "http",
             "path": "/research/stream", "raw_path": b"/research/stream", "query_string": b"",
             "headers": [(b"content-type", b"application/json")],
             "client": ("test", 1), "server": ("test", 80), "root_path": ""}
    await asyncio.wait_for(app(scope, receive, send), timeout=10)


def test_early_event_reaches_asgi_client_before_pipeline_finishes(monkeypatch):
    release, finished = Event(), Event()
    def fake(question, *, memory_path, on_event):
        on_event(event("planner now"))
        assert release.wait(5), "consumer did not receive progress before completion"
        finished.set()
        return ResearchState(question=question, final_report="done")
    monkeypatch.setattr("api.server.run_research_pipeline", fake)
    chunks = []
    def receive_chunk(chunk):
        chunks.append(chunk)
        if "planner now" in chunk:
            assert not finished.is_set()
            release.set()
    try:
        asyncio.run(asgi_request("test", receive_chunk))
    finally:
        release.set()
    assert finished.is_set()
    assert parse_frames("".join(chunks))[-1]["type"] == "workflow_completed"


def test_stream_failure_is_safe_and_terminal(monkeypatch):
    def fake(question, *, memory_path, on_event):
        on_event(event("starting"))
        raise RuntimeError("secret key /private/path prompt")
    monkeypatch.setattr("api.server.run_research_pipeline", fake)
    response = TestClient(app).post("/research/stream", json={"question": "test"})
    events = parse_frames(response.text)
    assert [e["type"] for e in events] == ["stage_started", "workflow_failed"]
    assert "secret" not in response.text and "private" not in response.text


def test_concurrent_streams_are_request_local(monkeypatch):
    def fake(question, *, memory_path, on_event):
        on_event(event(question))
        return ResearchState(question=question, final_report=question)
    monkeypatch.setattr("api.server.run_research_pipeline", fake)
    chunks = {"A": [], "B": []}
    async def run():
        await asyncio.gather(*(asgi_request(q, chunks[q].append) for q in chunks))
    asyncio.run(run())
    for q in chunks:
        events = parse_frames("".join(chunks[q]))
        assert events[0]["message"] == q
        assert events[-1]["data"]["report"] == q
