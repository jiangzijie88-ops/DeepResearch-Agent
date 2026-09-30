"""Incremental SSE parsing for the Streamlit HTTP client."""

import json


def iter_workflow_events(lines):
    data = []
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if not line:
            if data:
                event = json.loads("\n".join(data))
                if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                    raise ValueError("Invalid workflow event")
                yield event
                data = []
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        elif line.startswith((":", "event:", "id:", "retry:")):
            continue
        else:
            raise ValueError("Invalid SSE frame")
    if data:
        raise ValueError("Truncated SSE frame")
