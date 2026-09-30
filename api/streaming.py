"""Request-local bridge from a synchronous pipeline to SSE."""

import asyncio
import json
import logging
from queue import Empty, Full, Queue
from threading import Event, Thread

from openai import APIConnectionError, APIStatusError, APITimeoutError

from workflow.events import WorkflowEvent, completion_data


logger = logging.getLogger(__name__)


def encode_sse(event: WorkflowEvent) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"


def safe_error(error: Exception) -> str:
    if isinstance(error, APITimeoutError):
        return "模型服务响应超时，请稍后重试。"
    if isinstance(error, APIConnectionError):
        return "模型服务连接中断，请检查后端网络或代理后重试。"
    if isinstance(error, APIStatusError) and error.status_code == 402:
        return "模型账户余额不足，请充值或更换 API 密钥。"
    return "研究过程中发生错误，请检查后端日志后重试。"


async def stream_events(run):
    """Run calls the pipeline with an event sink and returns ResearchState.

    Closing the stream releases queue backpressure. It does not forcibly kill
    an in-flight model request: the daemon worker may finish the current run.
    """
    queue = Queue(maxsize=128)
    closed = Event()
    end = object()

    def put(item):
        while not closed.is_set():
            try:
                queue.put(item, timeout=0.1)
                return
            except Full:
                continue

    def on_event(event):
        # The API owns exactly one terminal event after run returns/raises.
        if event.type not in {"workflow_completed", "workflow_failed"}:
            put(event)

    def worker():
        try:
            state = run(on_event)
            put(WorkflowEvent(type="workflow_completed", stage="final", message="研究完成",
                              data=completion_data(state)))
        except Exception as error:
            logger.exception("Streaming research failed")
            put(WorkflowEvent(type="workflow_failed", stage="workflow", message=safe_error(error)))
        finally:
            put(end)

    thread = Thread(target=worker, name="research-stream", daemon=True)
    thread.start()
    try:
        while True:
            try:
                item = await asyncio.to_thread(queue.get, True, 1)
            except Empty:
                yield ": keep-alive\n\n"
                continue
            if item is end:
                break
            yield encode_sse(item)
    finally:
        closed.set()
