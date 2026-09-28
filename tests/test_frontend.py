import json
from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest


APP = str(Path(__file__).resolve().parents[1] / "frontend" / "app.py")


def submit(monkeypatch, response=None, error=None, question="测试问题"):
    def post(url, *, json, timeout):
        assert url == "http://127.0.0.1:8000/research"
        assert json == {"question": question.strip()}
        assert timeout == 600
        if error:
            raise error
        return response

    monkeypatch.setattr(requests, "post", post)
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.text_area[0].input(question)
    return app.button[0].click().run()


def response_for(payload, status=200):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(payload).encode("utf-8")
    return response


def test_frontend_displays_report_and_evidence(monkeypatch):
    response = response_for({
        "question": "测试问题", "status": "completed", "report": "# 研究报告",
        "evidence_count": 1, "evidence": [{
            "title": "示例论文", "year": 2025, "citations": 8,
            "venue": "Demo Journal", "source": "OpenAlex", "verified": True,
        }],
    })
    app = submit(monkeypatch, response=response)
    assert not app.exception
    assert any(item.value == "# 研究报告" for item in app.markdown)
    assert not any("正在生成报告，请稍等" in item.value for item in app.info)
    assert len(app.dataframe) == 1
    row = app.dataframe[0].value.iloc[0]
    assert row["Title"] == "示例论文"
    assert row["Citations"] == 8
    assert list(row.index) == ["Title", "Year", "Citations", "Venue", "Source", "Verified"]
    app.run()
    assert len(app.dataframe) == 1  # Keep results across Streamlit reruns.


def test_frontend_rejects_whitespace_without_request(monkeypatch):
    def unexpected_request(*args, **kwargs):
        pytest.fail("blank input must not contact the API")

    monkeypatch.setattr(requests, "post", unexpected_request)
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.text_area[0].input("   ")
    app.button[0].click().run()
    assert not app.exception
    assert len(app.warning) == 1


@pytest.mark.parametrize("error, message", [
    (requests.Timeout("private details"), "超时"),
    (requests.ConnectionError("private details"), "无法连接"),
])
def test_frontend_handles_transport_errors(monkeypatch, error, message):
    app = submit(monkeypatch, error=error)
    assert not app.exception
    assert message in app.error[0].value
    assert "private details" not in app.error[0].value
    assert not any("正在生成报告" in item.value for item in app.info)
    if isinstance(error, requests.ConnectionError):
        assert any("python -m uvicorn api.server:app" in item.value for item in app.code)


def test_frontend_reports_http_status_without_leaking_body(monkeypatch):
    app = submit(monkeypatch, response=response_for({"detail": "secret-token"}, 500))
    assert not app.exception
    assert "500" in app.error[0].value
    assert "secret-token" not in app.error[0].value


def test_frontend_explains_model_balance_error(monkeypatch):
    app = submit(monkeypatch, response=response_for({}, 402))
    assert not app.exception
    assert "余额不足" in app.error[0].value


def test_frontend_handles_invalid_json(monkeypatch):
    response = response_for({})
    response._content = b"not json"
    app = submit(monkeypatch, response=response)
    assert not app.exception
    assert "格式" in app.error[0].value


def test_frontend_explains_empty_evidence(monkeypatch):
    app = submit(monkeypatch, response=response_for({
        "question": "测试问题", "status": "completed", "report": "没有足够证据",
        "evidence_count": 0, "evidence": [],
    }))
    assert not app.exception
    assert any("证据" in item.value for item in app.info)
